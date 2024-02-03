# Thanos Kube Chaos - Kubernetes Chaos Engineering Tool

Thanos Kube Chaos is an open-source chaos engineering tool designed to induce controlled failures in Kubernetes clusters, drawing inspiration from Netflix Chaos Monkey. It equips users with a range of functions to simulate diverse failure scenarios, allowing them to assess and enhance the resilience of applications and infrastructure in Kubernetes environments.

## Overview
Thanos Kube Chaos leverages the Kubernetes Python client to interact with the cluster, offering features such as pod deletions, service deletions, node evictions, network latency injection, and simulated disk I/O chaos. The tool aims to provide a comprehensive testing framework for Kubernetes, enabling users to proactively identify and address vulnerabilities in their systems.

## Features
# List Pods:
Retrieve the names of pods in specified namespaces.
# List Running Pods:
Retrieve the names of running pods in specified namespaces.
# Delete Pod:
Delete a specific pod in a given namespace.
# Delete Random Running Pod:
Delete a randomly selected running pod, optionally matching a regex pattern.
# Delete Services:
Delete all services in specified namespaces.
# Delete Nodes:
Delete specific nodes from the Kubernetes cluster.
# Network Chaos Testing:
Simulate network chaos by introducing latency to a specified network interface.
# Resource Limit Configuration:
Set resource limits (CPU and memory) for a specific pod in a given namespace.
# Node Eviction:
Trigger the eviction of a specific node from the cluster.
# Execute Command in Pod:
Run a command inside a specific pod in a given namespace.
# Simulate Disk I/O Chaos:
Simulate high disk I/O for a specific pod by creating a test file.
# Retrieve Pod Volumes:
Retrieve the volumes attached to a specific pod in a given namespace.
# Starve Pod Resources:
Starve resources (CPU and memory) for a randomly selected running pod.


### Clone the repository:

```
git clone https://github.com/angu10/project_thanos.git
cd thanos-kube-chaos

```

### Installation

```
pip install -r requirements.txt
```

### Usage

Before using the `KubeManager` class, ensure that your Kubernetes configuration file (`kubeconfig` or `kubeconfig.yaml`) is loaded. The configuration file provides the necessary credentials and cluster information.

You can either set the `KUBECONFIG` environment variable to the path of your configuration file:

```
export KUBECONFIG=/path/to/your/kubeconfig.yaml
```
or use the config.load_kube_config() function in your Python script

```
from kubernetes import client, config
config.load_kube_config()

```

## Example 

```
# Import necessary modules
from thanos_kube_chaos.kube_manager import KubeManager

# Example: Creating a KubeManager instance with a list of namespaces
kube_manager = KubeManager(namespaces=['namespace1', 'namespace2'])

# Example: Listing the names of all pods in the specified namespaces
pod_names = kube_manager.get_pod_names()
print("Pod Names:", pod_names)

# Example: Deleting a randomly selected running pod
kube_manager.delete_random_running_pod()

# Example: Simulating network chaos with a delay of 10 seconds
kube_manager.test_network_chaos(delay_time=10)

# Example: Setting resource limits for a specific pod
kube_manager.set_resource_limits(pod_name='example-pod', namespace='example-namespace', cpu_limit='500m', memory_limit='256Mi')

# Example: Triggering node eviction for a specific node
kube_manager.trigger_node_eviction(node_name='example-node')

# Example: Simulating disk I/O chaos for a specific pod
kube_manager.simulate_disk_io_chaos(io_intensity=10, pod_name_regex='example-pod.*', container_name='example-container')

# Example: Retrieving the volumes of a specific pod
volumes = kube_manager.get_pod_volumes(pod_name='example-pod', namespace='example-namespace')
print("Pod Volumes:", volumes)

# Example: Starving resources for a randomly selected pod
kube_manager.starve_random_pod_resources(cpu_limit='200m', memory_limit='128Mi')


```