import unittest
from unittest.mock import MagicMock, patch
from thanos_kube_chaos.kube_manager import KubeManager
from kubernetes.client.rest import ApiException


class TestKubeManager(unittest.TestCase):

    @patch("kubernetes.client.CoreV1Api.list_namespaced_pod")
    def test_list_pods(self, mock_list_namespaced_pod):

        # Configure the MagicMocks
        mock_pod1 = MagicMock()
        mock_pod1.metadata.name = "pod1"

        mock_pod2 = MagicMock()
        mock_pod2.metadata.name = "pod2"

        mock_list_namespaced_pod.return_value.items = [mock_pod1, mock_pod2]

        # Create KubeManager
        kube_manager = KubeManager(namespaces=["default"])

        # Call method under test
        pods = kube_manager.list_pods()

        # Assert
        self.assertEqual(len(pods), 2)
        self.assertEqual(pods[0].metadata.name, "pod1")
        self.assertEqual(pods[1].metadata.name, "pod2")

    def test_get_node_interface(self):
        manager = KubeManager(["default"])

        mock_return_value = {"eth0": [MagicMock()]}
        with patch("psutil.net_if_addrs", return_value=mock_return_value):
            interface = manager.get_node_interface()

        self.assertEqual(interface, None)

    @patch("kubernetes.client.CoreV1Api.delete_namespaced_pod")
    def test_delete_pod(self, mock_delete_pod):
        manager = KubeManager(["default"])

        manager.delete_pod("mypod", "default")

        mock_delete_pod.assert_called_with(name="mypod", namespace="default")

    @patch("kubernetes.client.CoreV1Api.delete_namespaced_pod")
    def test_delete_pod_handles_exception(self, mock_delete_pod):
        mock_delete_pod.side_effect = ApiException()

        manager = KubeManager(["default"])
        manager.delete_pod("mypod", "default")

        # Assert exception handled gracefully
        mock_delete_pod.assert_called()


if __name__ == "__main__":
    unittest.main()
