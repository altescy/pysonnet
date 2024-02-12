# 📜 Pysonnet

[![CI](https://github.com/altescy/pysonnet/actions/workflows/ci.yml/badge.svg)](https://github.com/altescy/pysonnet/actions/workflows/ci.yml)
[![Python version](https://img.shields.io/pypi/pyversions/pysonnet)](https://github.com/altescy/pysonnet)
[![License](https://img.shields.io/github/license/altescy/pysonnet)](https://github.com/altescy/pysonnet/blob/main/LICENSE)
[![pypi version](https://img.shields.io/pypi/v/pysonnet)](https://pypi.org/project/pysonnet/)

A pure Python implementation of the Jsonnet language.

**Features**:
- **Pure Python Implementation**: Fully written in Python, ensuring compatibility and ease of integration with Python projects.
- **No External Dependencies**: Operates independently without the need for any external libraries, simplifying installation and use.

> [!IMPORTANT]
> Pysonnet is in the early stages of development.
> While it supports all Jsonnet syntax, it lacks some standard library features, and users might encounter bugs.

## Installation

```shell
pip install pysonnet
```

## Usage

Evaluate a jsonnet file and generate a JSON string:

```python
import pysonnet

json_string = pysonnet.evaluate_file("path/to/file.jsonnet", ext_vars={...})
```

Load a string and generate a Python object:

```python
import pysonnet

output = pysonnet.loads(
    """
    local Person(name='Alice') = {
      name: name,
      welcome: 'Hello ' + name + '!',
    };
    {
      person1: Person(),
      person2: Person('Bob'),
    }
    """
)
assert output == {
    "person1": {
        "name": "Alice",
        "welcome": "Hello Alice!"
    },
    "person2": {
        "name": "Bob",
        "welcome": "Hello Bob!"
    }
}
```

Evaluate file from command line:

```shell
pysonnet path/to/file.jsonnet
```
