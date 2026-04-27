from bmo.faces import FaceState, valid_transition


def test_states_exist():
    assert FaceState.IDLE.value == "idle"
    assert FaceState.LISTENING.value == "listening"
    assert FaceState.THINKING.value == "thinking"
    assert FaceState.SPEAKING.value == "speaking"
    assert FaceState.ERROR.value == "error"


def test_any_state_to_any_is_allowed():
    for a in FaceState:
        for b in FaceState:
            assert valid_transition(a, b) is True
