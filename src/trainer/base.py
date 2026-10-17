# Modified from https://github.com/huggingface/transformers/blob/v4.45.1/src/transformers/trainer.py

import logging
import os
from typing import Any, Dict, List, Optional, Union

from torch.utils.data import Dataset
from transformers import Trainer
from transformers.trainer_utils import PREFIX_CHECKPOINT_DIR

logger = logging.getLogger(__name__)


def _harmonic_mean(values, eps=1e-12):
    clean_values = []

    for value in values:
        if value is None:
            return None
        clean_values.append(max(float(value), eps))

    if not clean_values:
        return None

    return len(clean_values) / sum(1.0 / value for value in clean_values)


def _get_metric(metrics, key):
    if key in metrics:
        return metrics[key]

    eval_key = f"eval_{key}"
    if eval_key in metrics:
        return metrics[eval_key]

    return None


def _set_proxy_metric(metrics, key, value):
    # Store both names to be safe:
    # - Agg_proxy appears clearly in trainer_state.json
    # - eval_Agg_proxy works reliably with metric_for_best_model
    metrics[key] = value
    metrics[f"eval_{key}"] = value


def add_proxy_scores(metrics, baseline_model_utility=None):
    required_keys = [
        "extraction_strength",
        "exact_memorization",
        "forget_Q_A_Prob",
        "forget_truth_ratio",
        "mia_loss",
        "mia_zlib",
        "mia_min_k",
        "mia_min_k_plus_plus",
        "model_utility",
        "forget_Q_A_gibberish",
    ]

    if any(_get_metric(metrics, key) is None for key in required_keys):
        return metrics

    extraction_strength = float(_get_metric(metrics, "extraction_strength"))
    exact_memorization = float(_get_metric(metrics, "exact_memorization"))
    forget_q_a_prob = float(_get_metric(metrics, "forget_Q_A_Prob"))
    forget_truth_ratio = float(_get_metric(metrics, "forget_truth_ratio"))

    mia_loss = float(_get_metric(metrics, "mia_loss"))
    mia_zlib = float(_get_metric(metrics, "mia_zlib"))
    mia_min_k = float(_get_metric(metrics, "mia_min_k"))
    mia_min_k_plus_plus = float(_get_metric(metrics, "mia_min_k_plus_plus"))

    model_utility = float(_get_metric(metrics, "model_utility"))
    forget_q_a_gibberish = float(_get_metric(metrics, "forget_Q_A_gibberish"))

    mem_proxy = _harmonic_mean([
        1.0 - extraction_strength,
        1.0 - exact_memorization,
        1.0 - forget_q_a_prob,
        1.0 - forget_truth_ratio,
    ])

    privacy_proxy = _harmonic_mean([
        mia_loss,
        mia_zlib,
        mia_min_k,
        mia_min_k_plus_plus,
    ])

    if baseline_model_utility is not None and baseline_model_utility > 0:
        scaled_model_utility = min(model_utility / baseline_model_utility, 1.0)
    else:
        scaled_model_utility = model_utility

    utility_proxy = _harmonic_mean([
        scaled_model_utility,
        forget_q_a_gibberish,
    ])

    agg_proxy = _harmonic_mean([
        mem_proxy,
        privacy_proxy,
        utility_proxy,
    ])

    selection_proxy = _harmonic_mean([
        mem_proxy,
        utility_proxy,
    ])

    _set_proxy_metric(metrics, "Mem_proxy", mem_proxy)
    _set_proxy_metric(metrics, "Privacy_proxy", privacy_proxy)
    _set_proxy_metric(metrics, "Utility_proxy", utility_proxy)
    _set_proxy_metric(metrics, "Agg_proxy", agg_proxy)
    _set_proxy_metric(metrics, "Selection_proxy", selection_proxy)
    _set_proxy_metric(metrics, "scaled_model_utility_proxy", scaled_model_utility)

    return metrics


# When using custom evaluators without an eval dataset, pass a dummy value
# to prevent Trainer from raising on eval_dataset=None when eval_strategy is set
_EVAL_PLACEHOLDER = "_EVAL_PLACEHOLDER"


class FinetuneTrainer(Trainer):
    def __init__(self, evaluators=None, template_args=None, *args, **kwargs):
        self.evaluators = evaluators
        self.template_args = template_args
        if kwargs.get("eval_dataset") is None and evaluators:
            kwargs["eval_dataset"] = _EVAL_PLACEHOLDER
        super().__init__(*args, **kwargs)

    def evaluate(
        self,
        eval_dataset: Optional[Union[Dataset, Dict[str, Dataset]]] = None,
        ignore_keys: Optional[List[str]] = None,
        metric_key_prefix: str = "eval",
        trial: Dict[str, Any] = None,
    ) -> Dict[str, float]:
        # Run a custom evaluator and save results
        if self.evaluators and self.accelerator.is_local_main_process:
            if self.accelerator.num_processes != 1:
                logger.warning(
                    "Custom evaluator can be run with this Trainer only when a single accelerator process is running."
                )
                return {}

            run_dir = self._get_output_dir(trial=trial)
            checkpoint_folder = f"{PREFIX_CHECKPOINT_DIR}-{self.state.global_step}"
            output_dir = os.path.join(run_dir, checkpoint_folder, "evals")
            os.makedirs(output_dir, exist_ok=True)
            eval_metrics = {}
            for _, evaluator in self.evaluators.items():
                eval_args = {
                    "output_dir": output_dir,
                    "template_args": self.template_args,
                    "model": self.model,
                    "tokenizer": self.processing_class,
                }
                eval_metrics.update(evaluator.evaluate(**eval_args))
            # BEST_AGG_MUSE_SELECTION_PATCH
            # Add an aggregate checkpoint-selection metric for MUSE-style runs.
            # Higher is better. This lets HF Trainer keep the best checkpoint.
            def _bestagg_float_metric(_name, _default=None):
                _v = eval_metrics.get(_name, eval_metrics.get(f"eval_{_name}", _default))
                try:
                    return float(_v)
                except Exception:
                    return None

            _retain = _bestagg_float_metric("retain_knowmem_ROUGE")
            _forget_know = _bestagg_float_metric("forget_knowmem_ROUGE")
            _forget_verb = _bestagg_float_metric("forget_verbmem_ROUGE")
            _extract = _bestagg_float_metric("extraction_strength")

            if all(v is not None for v in [_retain, _forget_know, _forget_verb, _extract]):
                _utility_proxy = max(0.0, min(1.0, _retain))
                _memory_proxy = 1.0 - ((_forget_know + _forget_verb + _extract) / 3.0)
                _memory_proxy = max(0.0, min(1.0, _memory_proxy))

                if _utility_proxy + _memory_proxy > 0:
                    _best_agg = 2.0 * _utility_proxy * _memory_proxy / (_utility_proxy + _memory_proxy)
                else:
                    _best_agg = 0.0

                eval_metrics["best_agg"] = _best_agg
                eval_metrics["eval_best_agg"] = _best_agg
            if not hasattr(self, "_proxy_baseline_model_utility"):
                self._proxy_baseline_model_utility = None

            if self._proxy_baseline_model_utility is None and _get_metric(eval_metrics, "model_utility") is not None:
                self._proxy_baseline_model_utility = float(_get_metric(eval_metrics, "model_utility"))

            eval_metrics = add_proxy_scores(
                eval_metrics,
                baseline_model_utility=self._proxy_baseline_model_utility,
            )

            self.log(eval_metrics)
            return eval_metrics

        if eval_dataset is None or eval_dataset == _EVAL_PLACEHOLDER:
            return {}
        # Run the default HF Trainer evaluate method when eval dataset is provided
        return super().evaluate(eval_dataset, ignore_keys, metric_key_prefix)
