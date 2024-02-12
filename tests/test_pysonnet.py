import pysonnet


def test_version() -> None:
    assert pysonnet.__version__ == "0.1.0"


def test_loads() -> None:
    s = """
    local Person(name='Alice') = {
      name: name,
      welcome: 'Hello ' + name + '!',
    };
    {
      person1: Person(),
      person2: Person('Bob'),
    }
    """
    value = pysonnet.loads(s)
    assert value == {
        "person1": {
            "name": "Alice",
            "welcome": "Hello Alice!",
        },
        "person2": {
            "name": "Bob",
            "welcome": "Hello Bob!",
        },
    }
