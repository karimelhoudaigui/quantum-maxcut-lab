import pytest

from api.schemas import GraphFamily, GraphResponse


@pytest.fixture
def minimal_graph_payload():
    return GraphResponse(
        family=GraphFamily.path,
        n_nodes=2,
        edges=[{"i": 0, "j": 1, "w": 1.0}],
        positions=[{"id": 0, "x": 0.0, "y": 0.0}, {"id": 1, "x": 1.0, "y": 0.0}],
        mapping_error=0.0,
        descriptors={},
    )
