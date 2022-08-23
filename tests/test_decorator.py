import ast
from argparse import Namespace
from typing import Tuple

from flake8.main.application import Application

from flake8_trio import Error_codes, Plugin, Statement, regex_has_decorator


def dec_list(*decorators: str) -> ast.Module:
    source = ""
    for dec in decorators:
        source += f"@{dec}\n"
    source += "async def f():\n  bar()"
    tree = ast.parse(source)
    return tree


def wrap(decorators: Tuple[str, ...], decs2: str) -> bool:
    tree = dec_list(*decorators)
    assert isinstance(tree.body[0], ast.AsyncFunctionDef)
    return regex_has_decorator(tree.body[0].decorator_list, decs2)


def test_basic():
    assert wrap(("foo",), "foo")
    assert wrap(("foo", "bar"), "foo")
    assert wrap(("bar", "foo"), "foo")

    assert not wrap(("foo",), "foob")


def test_dotted():
    assert wrap(("foo.bar",), "foo.bar")

    assert not wrap(("foo.bar",), "foo")
    assert not wrap(("foo.bar",), "bar")

    assert not wrap(("foo",), "foo.bar")
    assert not wrap(("bar",), "foo.bar")

    assert not wrap(("foo.bar.jane",), "foo.bar")
    assert not wrap(("foo.bar",), "foo.bar.jane")
    assert not wrap(("jane.foo.bar",), "foo.bar")
    assert not wrap(("foo.bar",), "jane.foo.bar")


def test_multidotted():
    assert wrap(("foo.bar.jane",), "foo.bar.jane")
    assert not wrap(("foo.bar",), "foo.bar.jane")
    assert not wrap(("foo.bar.jane",), "foo.bar")


def test_wildcard():
    assert wrap(("foo",), "*")
    assert wrap(("foo.bar",), "*")
    assert not wrap(("foo",), "foo.*")
    assert wrap(("foo.bar",), "foo.*")
    assert not wrap(("bar.foo",), "foo.*")


def test_wildcard_regex():
    assert wrap(("foo",), "foo*")
    assert wrap(("foobar",), "foo*")
    assert not wrap(("foobar.bar",), "foo*")


def test_at():
    assert wrap(("foo",), "@foo")
    assert wrap(("foo.bar",), "@foo.bar")


def test_plugin():
    tree = dec_list("app.route")
    plugin = Plugin(tree)
    assert tuple(plugin.run())

    plugin.options = Namespace(no_checkpoint_warning_decorators=["app.route"])
    assert not tuple(plugin.run())


def test_command_line_1(capfd):
    Application().run(
        [
            "--ignore=E,F,W",
            "--no-checkpoint-warning-decorators=app.route",
            "tests/trio_options.py",
        ]
    )
    out, err = capfd.readouterr()
    assert not out and not err


expected_out = (
    "tests/trio_options.py:2:1: TRIO107: "
    + Error_codes["TRIO107"].format("exit", Statement("function definition", 2))
    + "\n"
)


def test_command_line_2(capfd):
    Application().run(
        [
            "--ignore=E,F,W",
            "--no-checkpoint-warning-decorators=app",
            "tests/trio_options.py",
        ]
    )
    out, err = capfd.readouterr()
    assert out == expected_out and not err


def test_command_line_3(capfd):
    Application().run(
        [
            "--ignore=E,F,W",
            "tests/trio_options.py",
        ]
    )
    out, err = capfd.readouterr()
    assert out == expected_out and not err
