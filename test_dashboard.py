import marimo

__generated_with = "0.16.2"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    return mo,


@app.cell
def _(mo):
    mo.md("# Test Dashboard")
    return


@app.cell
def _(mo):
    test_button = mo.ui.button(label="Click Me")
    return test_button,


@app.cell
def _(mo, test_button):
    mo.vstack([
        test_button,
        mo.md(f"Button clicked: {test_button.value if test_button.value else 'Not yet'}")
    ])
    return


if __name__ == "__main__":
    app.run()