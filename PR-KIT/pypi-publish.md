# Publishing the Python engine on PyPI (you do this: it needs your PyPI account)

1. Create an account on pypi.org and on test.pypi.org; enable 2FA; create an API token for each.
2. The name `ghostmark-image` must be free: check https://pypi.org/project/ghostmark-image/ (404 = free). If taken, change `name` in `python/pyproject.toml`; the import name stays `ghostmark`.
3. Build and upload (from the `python/` folder):
```bash
pip install build twine
python -m build
twine upload --repository testpypi dist/*      # try on TestPyPI first
twine upload dist/*
```
4. Test: `pip install "ghostmark-image[files]"` in a fresh virtualenv, then `ghostmark --version`.
5. Then change the README install line from `pip install ./python[files]` to `pip install "ghostmark-image[files]"`.
