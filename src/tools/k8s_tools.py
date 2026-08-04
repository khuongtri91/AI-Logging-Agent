from langchain_core.tools import tool


@tool
def restart_kubernetes_pod(
    pod_name: str,
    namespace: str = "default",
    reason: str = "",
) -> str:
    """
    Restart a Kubernetes pod by deleting it.

    The pod is expected to be recreated by its Deployment or ReplicaSet.
    This action can disrupt service, so it must only run after explicit user
    approval.

    Args:
        pod_name: Name of the pod to restart.
        namespace: Kubernetes namespace.
        reason: Reason for restarting the pod.

    Returns:
        A simulated restart result.
    """
    print(f"\n{'=' * 70}")
    print("PLACEHOLDER: Would restart Kubernetes pod")
    print(f"{'=' * 70}")
    print(f"Namespace: {namespace}")
    print(f"Pod Name:  {pod_name}")
    print(f"Reason:    {reason}")
    print(f"Action:    kubectl delete pod {pod_name} -n {namespace}")
    print("Expected:  Pod will be recreated automatically by ReplicaSet/Deployment")
    print(f"{'=' * 70}\n")

    return (
        f"[SIMULATED] Successfully restarted pod '{pod_name}' in namespace "
        f"'{namespace}'. Pod will be recreated automatically."
    )


def get_k8s_tools() -> list:
    """Get Kubernetes action tools."""
    return [restart_kubernetes_pod]
