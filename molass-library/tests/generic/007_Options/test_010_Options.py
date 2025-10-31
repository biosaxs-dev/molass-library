"""
    test Options
"""

def test_01_set_and_get():
    from molass.Global.Options import set_molass_options, get_molass_options
    set_molass_options(mapped_trimming=False, flowchange='auto', developer_mode=True)
    assert get_molass_options('mapped_trimming') is False
    assert get_molass_options('flowchange') == 'auto'
    assert get_molass_options('developer_mode') is True

def test_02_get_multiple():
    from molass.Global.Options import set_molass_options, get_molass_options
    set_molass_options(mapped_trimming=True, flowchange=False, developer_mode=False)
    values = get_molass_options('mapped_trimming', 'flowchange', 'developer_mode')
    assert values == [True, False, False]

def test_03_set_exceptions():
    from molass.Global.Options import set_molass_options
    try:
        set_molass_options(non_existing_option=True)
    except ValueError as e:
        assert str(e) == "No such global option: non_existing_option"
    else:
        assert False, "Expected ValueError for non-existing option"