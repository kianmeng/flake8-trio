from contextlib import asynccontextmanager

import trio


async def foo():
    try:
        ...
    finally:
        with trio.move_on_after(deadline=30) as s:
            s.shield = True
            await foo()

    try:
        pass
    finally:
        with trio.move_on_after(30) as s:
            s.shield = True
            await foo()

    try:
        pass
    finally:
        await foo()  # error: 8, Statement("try/finally", lineno-3)

    try:
        pass
    finally:
        with trio.move_on_after(30) as s:
            await foo()  # error: 12, Statement("try/finally", lineno-4)

    try:
        pass
    finally:
        with trio.move_on_after(30):
            await foo()  # error: 12, Statement("try/finally", lineno-4)

    bar = 10

    try:
        pass
    finally:
        with trio.move_on_after(bar) as s:
            s.shield = True
            await foo()

    try:
        pass
    finally:
        with trio.move_on_after(bar) as s:
            s.shield = False
            s.shield = True
            await foo()

    try:
        pass
    finally:
        with trio.move_on_after(bar) as s:
            s.shield = True
            await foo()
            s.shield = False
            await foo()  # error: 12, Statement("try/finally", lineno-7)
            s.shield = True
            await foo()

    try:
        pass
    finally:
        with open("bar"):
            await foo()  # error: 12, Statement("try/finally", lineno-4)
    try:
        pass
    finally:
        with open("bar"):
            pass
    try:
        pass
    finally:
        with trio.move_on_after():
            await foo()  # error: 12, Statement("try/finally", lineno-4)
    try:
        pass
    finally:
        with trio.move_on_after(foo=bar):
            await foo()  # error: 12, Statement("try/finally", lineno-4)
    try:
        pass
    finally:
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
    try:
        pass
    finally:
        with trio.CancelScope(shield=True):
            await foo()  # error: 12, Statement("try/finally", lineno-4)
    try:
        pass
    finally:
        with trio.CancelScope(deadline=30):
            await foo()  # error: 12, Statement("try/finally", lineno-4)
    try:
        pass
    finally:
        with trio.CancelScope(deadline=30, shield=(1 == 1)):
            await foo()  # safe in theory, error: 12, Statement("try/finally", lineno-4)
    try:
        pass
    finally:
        myvar = True
        with trio.open_nursery(10) as s:
            s.shield = myvar
            await foo()  # safe in theory, error: 12, Statement("try/finally", lineno-6)
    try:
        pass
    finally:
        with trio.CancelScope(deadline=30, shield=True):
            with trio.move_on_after(30):
                await foo()  # safe
    try:
        pass
    finally:
        async for i in trio.bypasslinters:  # error: 8, Statement("try/finally", lineno-3)
            pass
    try:
        pass
    finally:
        async with trio.CancelScope(  # error: 8, Statement("try/finally", lineno-3)
            deadline=30, shield=True
        ):
            await foo()  # safe

    with trio.CancelScope(deadline=30, shield=True):
        try:
            pass
        finally:
            await foo()  # error: 12, Statement("try/finally", lineno-3)


# change of functionality, no longer treated as safe
# https://github.com/Zac-HD/flake8-trio/issues/54
@asynccontextmanager
async def foo2():
    try:
        yield 1
    finally:
        await foo()  # error: 8, Statement("try/finally", lineno-3)


async def foo3():
    try:
        ...
    finally:
        with trio.move_on_after(30) as s, trio.fail_after(5):
            s.shield = True
            await foo()  # safe
        with trio.move_on_after(30) as s, trio.fail_after(5):
            await foo()  # TRIO102: 12, Statement("try/finally", lineno-7)
        with open(""), trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
        with trio.fail_after(5), trio.move_on_after(30) as s:
            s.shield = True
            await foo()  # safe in theory, error: 12, Statement("try/finally", lineno-12)


# New: except cancelled/baseexception are also critical
async def foo4():
    try:
        ...
    except ValueError:
        await foo()  # safe
    except trio.Cancelled:
        await foo()  # error: 8, Statement("trio.Cancelled", lineno-1)
    except BaseException:
        await foo()  # error: 8, Statement("BaseException", lineno-1)
    except:
        await foo()  # error: 8, Statement("bare except", lineno-1)


async def foo5():
    try:
        ...
    except trio.Cancelled:
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
    except BaseException:
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe
    except:
        with trio.CancelScope(deadline=30, shield=True):
            await foo()  # safe


# multiple errors on same line
# fmt: off
async def foo6():
    try:
        ...
    except trio.Cancelled:
        _ = await foo(), await foo()  # error: 12, Statement("trio.Cancelled", lineno-1) # error: 25, Statement("trio.Cancelled", lineno-1)
# fmt: on
