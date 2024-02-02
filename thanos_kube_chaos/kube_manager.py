import random
import kubernetes.client
from kubernetes import client, config
from kubernetes.client.rest import ApiException
from kubernetes.stream import stream
import re
import subprocess
import psutil
import socket
import time
import shutil


class KubeManager:
    """
    Class for managing Kubernetes resources and inducing chaos.

    Attributes:
    - namespaces (list): List of Kubernetes namespaces to operate on.
    - v1 (CoreV1Api): Instance of the Kubernetes CoreV1Api.
    """

    def __init__(self, namespaces):
        """
        Initializes the KubeManager.

        Parameters:
        - namespaces (list): List of Kubernetes namespaces.
        """
        config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.namespaces = namespaces

    def get_pod_names(self):
        """
        Retrieves the names of all pods in the specified namespaces.

        Returns:
        - pod_names (list): List of pod names.
        """
        pod_names = []
        for namespace in self.namespaces:
            print(f"working namespace: {namespace}")
            try:
                api_response = self.v1.list_namespaced_pod(namespace)
                for pod in api_response.items:
                    pod_names.append(pod.metadata.name)
            except ApiException as e:
                print(f"Exception when calling CoreV1Api->list_namespaced_pod: {e}")
        return pod_names

    def list_pods(self):
        """
        Lists all pods in the specified namespaces.

        Returns:
        - pods (list): List of pod objects.
        """
        pods = []
        for namespace in self.namespaces:
            try:
                api_response = self.v1.list_namespaced_pod(namespace)
                pods.extend(api_response.items)
            except ApiException as e:
                print(f"Exception when calling CoreV1Api->list_namespaced_pod: {e}")
        return pods

    def list_running_pod_names(self):
        """
        Lists names of running pods in the specified namespaces.

        Returns:
        - running_pod_names (dict): Dictionary of running pod names with corresponding namespaces.
        """
        running_pod_names = {}
        print("list_running_pod_names running now")
        for namespace in self.namespaces:
            print(f"Namespace {namespace}")
            pods = self.list_pods()
            for pod in pods:
                if pod.status.phase == "Running":
                    running_pod_names[pod.metadata.name] = pod.metadata.namespace
        return running_pod_names

    def delete_pod(self, pod_name, namespace):
        """
        Deletes a pod with the specified name in the given namespace.

        Parameters:
        - pod_name (str): Name of the pod to delete.
        - namespace (str): Namespace of the pod.
        """
        try:
            self.v1.delete_namespaced_pod(name=pod_name, namespace=namespace)
            print(f"Deleted pod: {pod_name} in namespace: {namespace}")
        except ApiException as e:
            print(f"Exception when calling CoreV1Api->delete_namespaced_pod: {e}")

    def delete_random_running_pod(self, pod_name_regex=None, exceptions=None):
        """
        Deletes a randomly selected running pod based on criteria.

        Parameters:
        - pod_name_regex (str): Regular expression for selecting pod names.
        - exceptions (set): Set of pod names to exclude from deletion.
        """
        if exceptions is None:
            exceptions = set()
        if pod_name_regex:
            filtered_pod_names = {
                pod_name: namespace
                for pod_name, namespace in self.list_running_pod_names().items()
                if re.match(pod_name_regex, pod_name) and pod_name not in exceptions
            }
            if filtered_pod_names:
                pod_name, namespace = random.choice(list(filtered_pod_names.items()))
                print(pod_name, namespace)
                self.delete_pod(pod_name, namespace)
            else:
                print("No matching running pods to delete.")
        else:
            available_pods = [
                pod
                for pod in self.list_running_pod_names().keys()
                if pod not in exceptions
            ]
            if available_pods:
                pod_name = random.choice(available_pods)
                namespace = self.list_running_pod_names()[pod_name]
                print(pod_name, namespace)
                self.delete_pod(pod_name, namespace)
            else:
                print("All running pods are in the exception list. Skipping deletion.")

    def delete_services(self):
        """
        Deletes all services in the specified namespaces.
        """
        for namespace in self.namespaces:
            try:
                services = self.v1.list_namespaced_service(namespace=namespace)
                for service in services.items:
                    self.v1.delete_namespaced_service(
                        name=service.metadata.name, namespace=namespace
                    )
                    print(
                        f"Deleted service: {service.metadata.name} in namespace: {namespace}"
                    )
            except ApiException as e:
                print(
                    f"Exception when calling CoreV1Api->delete_namespaced_service: {e}"
                )

    def delete_nodes(self, node_names):
        """
        Deletes nodes with the specified names.

        Parameters:
        - node_names (list): List of node names to delete.
        """
        for node_name in node_names:
            try:
                self.v1.delete_node(name=node_name)
                print(f"Deleted node: {node_name}")
            except ApiException as e:
                print(f"Exception when calling CoreV1Api->delete_node: {e}")

    def get_node_interface(self):
        """
        Retrieves the first non-loopback network interface.

        Returns:
        - interface (str): Network interface name.
        """
        interfaces = psutil.net_if_addrs()
        for interface, addresses in interfaces.items():
            for address in addresses:
                if address.family == socket.AF_INET and not address.address.startswith(
                    "127."
                ):
                    return interface

    def find_tc_path(self):
        """
        Finds the path to the 'tc' command.

        Returns:
        - tc_path (str): Path to the 'tc' command.
        """
        tc_path = shutil.which("tc")
        print(f"tc_path {tc_path}")
        if tc_path is None:
            raise Exception("unable to find tc")
        return tc_path

    def make_node_network_flaky(self, node_interface, tc=None, latency_ms=5000):
        """
        Makes the network on a node flaky by injecting latency.

        Parameters:
        - node_interface (str): Network interface on the node.
        - tc (str): Path to the 'tc' command (optional, default is None).
        - latency_ms (int): Latency to inject in milliseconds (default is 5000).
        """
        TC = tc
        if not tc:
            TC = self.find_tc_path()
        # Add latency
        cmd_add = f"{TC} qdisc add dev {node_interface} root netem delay {latency_ms}ms"
        subprocess.run(cmd_add.split(), check=True)
        # Clear latency after test
        cmd_del = f"{TC} qdisc del dev {node_interface} root"
        subprocess.run(cmd_del.split(), check=True)

    def test_network_chaos(self, delay_time=10):
        """
        Tests network chaos by injecting latency for a specified duration.

        Parameters:
        - delay_time (int): Duration of network chaos in seconds (default is 10).
        """
        node_interface = self.get_node_interface()
        if node_interface:
            try:
                self.make_node_network_flaky(node_interface, latency_ms=500)
                time.sleep(delay_time)
            finally:
                # Add cleanup steps if needed
                self.make_node_network_flaky(
                    node_interface, latency_ms=0
                )  # Restore normal network
        else:
            print("Unable to determine network interface.")

    def set_resource_limits(self, pod_name, namespace, cpu_limit, memory_limit):
        """
        Sets resource limits (CPU and memory) for a pod.

        Parameters:
        - pod_name (str): Name of the pod.
        - namespace (str): Namespace of the pod.
        - cpu_limit (str): CPU limit for the pod.
        - memory_limit (str): Memory limit for the pod.
        """
        try:
            # Retrieve the pod's current configuration
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)

            # Modify the pod's configuration to include resource limits
            container = pod.spec.containers[0]
            container.resources = client.V1ResourceRequirements(
                limits={"cpu": cpu_limit, "memory": memory_limit}
            )

            # Apply the updated configuration back to the cluster
            self.v1.replace_namespaced_pod(name=pod_name, namespace=namespace, body=pod)
        except ApiException as e:
            print(f"Exception when calling CoreV1Api->set_resource_limits: {e}")
            print(f"Error details {e.body}")

    def trigger_node_eviction(self, node_name):
        """
        Triggers the eviction of a node.

        Parameters:
        - node_name (str): Name of the node to evict.
        """
        try:
            eviction_body = client.V1beta1Eviction(
                api_version="policy/v1beta1",
                kind="Eviction",
                delete_options=client.V1DeleteOptions(),
            )
            self.v1beta.create_node_eviction(
                name=node_name, body=eviction_body, grace_period_seconds=0
            )
            print(f"Triggered eviction for node: {node_name}")
        except ApiException as e:
            print(f"Exception when calling CoreV1beta1Api->create_node_eviction: {e}")

    def execute_command_in_pod(self, pod_name, namespace, command, container_name=None):
        """
        Executes a command inside a pod.

        Parameters:
        - pod_name (str): Name of the pod.
        - namespace (str): Namespace of the pod.
        - command (str): Command to execute inside the pod.
        - container_name (str): Name of the container (optional, default is None).
        """
        try:
            # Specify the container name (assuming only one container in the pod)

            # Execute the command inside the pod
            exec_command = ["/bin/sh", "-c", command]
            resp = stream(
                self.v1.connect_get_namespaced_pod_exec,
                pod_name,
                namespace,
                command=exec_command,
                container=container_name,
                stderr=True,
                stdin=True,
                stdout=True,
                tty=False,
                _preload_content=False,
            )

            # Read and print the output of the command
            while resp.is_open():
                resp.update(timeout=1)
                if resp.peek_stdout():
                    print(resp.read_stdout().decode("utf-8"), end="")
                if resp.peek_stderr():
                    print(resp.read_stderr().decode("utf-8"), end="")

            resp.close()

        except ApiException as e:
            print(f"Exception when calling CoreV1Api: {e}")

    def simulate_disk_io_chaos(
        self, io_intensity, pod_name_regex=None, exceptions=None, container_name=None
    ):
        """
        Simulates disk I/O chaos on a randomly selected pod.

        Parameters:
        - io_intensity (int): Intensity of disk I/O chaos (size of testfile).
        - pod_name_regex (str): Regular expression for selecting pod names.
        - exceptions (set): Set of pod names to exclude from chaos.
        - container_name (str): Name of the container (optional, default is None).
        """
        running_pod_names = self.list_running_pod_names()
        print(f"Running Pods {running_pod_names}")

        if not running_pod_names:
            print(
                f"No running pods in namespace: {self.namespaces}. Skipping resource starvation."
            )
            return

        # Randomly select a running pod
        if pod_name_regex and exceptions:
            filtered_pod_names = {
                pod_name: namespace
                for pod_name, namespace in self.list_running_pod_names().items()
                if not re.match(pod_name_regex, pod_name)
            }
        else:
            filtered_pod_names = {
                pod_name: namespace
                for pod_name, namespace in self.list_running_pod_names().items()
            }

        if len(filtered_pod_names) > 0:
            pod_name = random.choice(list(filtered_pod_names.keys()))
            print(f"random pod name {pod_name}")
            try:
                # Create the /data directory in the pod (if it doesn't exist)
                create_data_dir_command = "mkdir -p /data"
                self.execute_command_in_pod(
                    pod_name,
                    filtered_pod_names[pod_name],
                    create_data_dir_command,
                    container_name,
                )
                # Command to simulate disk I/O chaos using 'dd' command
                command = (
                    f"dd if=/dev/zero of=/data/testfile bs=1M count={io_intensity}"
                )

                # Specify the container name (assuming only one container in the pod)

                exec_command = ["/bin/sh", "-c", command]

                # Execute the command inside the pod
                resp = stream(
                    self.v1.connect_get_namespaced_pod_exec,
                    pod_name,
                    filtered_pod_names[pod_name],
                    command=exec_command,
                    container=container_name,
                    stderr=True,
                    stdin=True,
                    stdout=True,
                    tty=False,
                    _preload_content=False,
                )

                # Read and print the output of the command
                print(resp)
                while resp.is_open():
                    resp.update(timeout=1)
                    if resp.peek_stdout():
                        print(resp.read_stdout(), end="")
                    if resp.peek_stderr():
                        print(resp.read_stderr(), end="")

                resp.close()

                print(
                    f"Simulated high disk I/O for pod: {pod_name} in namespace: {filtered_pod_names[pod_name]} (Intensity: {io_intensity})"
                )
            except ApiException as e:
                print(f"Exception when calling CoreV1Api: {e}")

    def get_pod_volumes(self, pod_name, namespace):
        """
        Retrieves volumes associated with a pod.

        Parameters:
        - pod_name (str): Name of the pod.
        - namespace (str): Namespace of the pod.

        Returns:
        - volumes (list): List of volumes associated with the pod.
        """
        try:
            pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            volumes = pod.spec.volumes
            return volumes
        except ApiException as e:
            print(f"Exception when calling read_namespaced_pod: {e}")
            return []

    def starve_random_pod_resources(
        self, cpu_limit=None, memory_limit=None, pod_name_regex=None, exceptions=None
    ):
        """
        Starves resources (CPU and memory) for a randomly selected pod.

        Parameters:
        - cpu_limit (str): CPU limit for the pod.
        - memory_limit (str): Memory limit for the pod.
        - pod_name_regex (str): Regular expression for selecting pod names.
        - exceptions (set): Set of pod names to exclude from resource starvation.
        """
        running_pod_names = self.list_running_pod_names()
        print(f"Running Pods {running_pod_names}")

        if not running_pod_names:
            print(
                f"No running pods in namespace: {self.namespaces}. Skipping resource starvation."
            )
            return

        # Randomly select a running pod
        if pod_name_regex and exceptions:
            filtered_pod_names = {
                pod_name: namespace
                for pod_name, namespace in self.list_running_pod_names().items()
                if not re.match(pod_name_regex, pod_name)
            }
        else:
            filtered_pod_names = {
                pod_name: namespace
                for pod_name, namespace in self.list_running_pod_names().items()
            }

        if len(filtered_pod_names) > 0:
            pod_name = random.choice(list(filtered_pod_names.keys()))
            print(f"random pod name {pod_name}")

            try:
                patch = []
                if cpu_limit:
                    patch.append(
                        {
                            "op": "replace",
                            "path": "/spec/containers/0/resources/limits/cpu",
                            "value": cpu_limit,
                        }
                    )
                if memory_limit:
                    patch.append(
                        {
                            "op": "replace",
                            "path": "/spec/containers/0/resources/limits/memory",
                            "value": memory_limit,
                        }
                    )
                print(f"namespace {filtered_pod_names[pod_name]}")
                print(patch)
                self.v1.patch_namespaced_pod(
                    name=pod_name, namespace=filtered_pod_names[pod_name], body=patch
                )
                print(
                    f"Starved resources for randomly selected pod: {pod_name} in namespace: {filtered_pod_names[pod_name]}"
                )
            except ApiException as e:
                print(f"Exception when calling CoreV1Api->patch_namespaced_pod: {e}")
                print(f"Error details {e.body}")
