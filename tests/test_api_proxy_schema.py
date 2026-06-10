from api.schemas import PipelineRunRequest


def test_pipeline_request_defaults_to_rydberg_xy(minimal_graph_payload):
    request = PipelineRunRequest(graph=minimal_graph_payload)
    assert request.proxy_hamiltonian.value == "rydberg_xy"


def test_pipeline_request_accepts_experimental_proxy(minimal_graph_payload):
    request = PipelineRunRequest(
        graph=minimal_graph_payload,
        proxy_hamiltonian="ising_zz",
    )
    assert request.proxy_hamiltonian.value == "ising_zz"
