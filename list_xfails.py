def pytest_collection_modifyitems(items):
    for item in items:
        for m in item.iter_markers("xfail"):
            reason = m.kwargs.get("reason") or (m.args[1] if len(m.args) > 1 else "")
            print(f"XFAIL | {item.nodeid} | {reason}")
