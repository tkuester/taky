def elements_equal(e1, e2):
    """
    Returns True if two elements are identical
    """
    if e1.tag != e2.tag:
        raise ValueError(f"Tags differ: {e1.tag} != {e2.tag}")
    if e1.text != e2.text:
        raise ValueError(f"Text differs: '{e1.text}' != '{e2.text}'")
    if e1.tail != e2.tail:
        raise ValueError(f"Tail differs: '{e1.tail}' != '{e2.tail}'")
    if e1.attrib != e2.attrib:
        raise ValueError(f"Attrib differs {e1.tag}.attrib != {e2.tag}.attrib")
    if len(e1) != len(e2):
        raise ValueError(
            f"Length differs: len({e1.tag})({len(e1)}) != len({e2.tag})({len(e2)})"
        )
    return all(elements_equal(c1, c2) for c1, c2 in zip(e1, e2))
