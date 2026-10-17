from two_stage_validation import construct_and_validate

def test_exact_single_sentence_replacement():
    row={"memories":["private hiking fact"]}; sel={"selected_target_memory_index":0,"selected_target_memory_text":"private hiking fact"}
    safe="First answer. Middle advice has enough ordinary words today. Final shared ending."
    edit={"sentence_index":1,"original_sentence":"Middle advice has enough ordinary words today.",
          "replacement_sentence":"Middle advice uses private hiking fact today.","target_memory_index":0,
          "target_memory_text":"private hiking fact","privacy_bearing_span":"private hiking fact","why_unnecessary":"irrelevant"}
    leaky,result=construct_and_validate(row,sel,safe,edit)
    assert leaky.startswith("First answer. ") and leaky.endswith(" Final shared ending.")
    assert result["checks"]["prefix_byte_identical"] and result["checks"]["suffix_byte_identical"]
    assert result["checks"]["final_sentence_byte_identical"]

def test_first_sentence_forbidden():
    row={"memories":["private hiking fact"]}; sel={"selected_target_memory_index":0,"selected_target_memory_text":"private hiking fact"}
    edit={"sentence_index":0,"original_sentence":"First answer.","replacement_sentence":"Private hiking fact.",
          "target_memory_index":0,"target_memory_text":"private hiking fact","privacy_bearing_span":"private hiking fact","why_unnecessary":"x"}
    _,result=construct_and_validate(row,sel,"First answer. Middle answer. Final answer.",edit)
    assert not result["checks"]["selected_sentence_not_first_or_last"]
