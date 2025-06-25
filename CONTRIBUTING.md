# MoBI_View pull request guidelines

Pull requests are always welcome, and we appreciate any help you give. Note that a code of conduct applies to all spaces managed by the MoBI_View project, including issues and pull requests. Please see the [Code of Conduct](CODE_OF_CONDUCT.md) for details.

When submitting a pull request, we ask you to check the following:

1. **Unit tests**, **documentation**, and **code style** are in order.
   See the Continuous Integration for up to date information on the current code style, tests, and any other requirements.

   It is also OK to submit work in progress if you're unsure of what this exactly means, in which case you'll likely be asked to make some further changes.

2. The contributed code will be **licensed under the same [license](LICENSE) as the rest of the repository**, If you did not write the code yourself, you must ensure the existing license is compatible and include the license information in the contributed files, or obtain permission from the original author to relicense the contributed code.


3. Before contributing to MoBI-View, please set up your local development environment:

```sh
git clone https://github.com/yourusername/MoBI-View.git
cd MoBI-View

# Create and activate a virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install all dependencies (including dev dependencies)
uv sync

# Install pre-commit hooks
pre-commit install
```

This setup ensures you have all the necessary development dependencies and tools to contribute effectively to the project.
