from invoke import task


@task
def build(c):
    c.run("pyinstaller mangadex_mass_uploader/main.spec")
