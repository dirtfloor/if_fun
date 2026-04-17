from if_fun.ids import Direction, EventId, ItemId, MobId, RoomId


def test_ids_are_distinct_str_subtypes() -> None:
    r = RoomId("entry_hall")
    i = ItemId("brass_key")
    m = MobId("rat")
    e = EventId("evt_0001")
    assert str(r) == "entry_hall"
    assert str(i) == "brass_key"
    assert str(m) == "rat"
    assert str(e) == "evt_0001"


def test_direction_opposite() -> None:
    assert Direction.NORTH.opposite() is Direction.SOUTH
    assert Direction.SOUTH.opposite() is Direction.NORTH
    assert Direction.EAST.opposite() is Direction.WEST
    assert Direction.WEST.opposite() is Direction.EAST
    assert Direction.UP.opposite() is Direction.DOWN
    assert Direction.DOWN.opposite() is Direction.UP


def test_direction_from_token_accepts_full_and_short() -> None:
    assert Direction.from_token("n") is Direction.NORTH
    assert Direction.from_token("NORTH") is Direction.NORTH
    assert Direction.from_token("up") is Direction.UP
    assert Direction.from_token("xyzzy") is None
