from unittest.mock import MagicMock
import botocore.exceptions

from app.services.bucket import is_file_exist  # Replace 'your_module' with your actual file/module name


def test_is_file_exist_true():
    mock_boto_client = MagicMock()
    # head_object does not raise an exception if file exists
    result = is_file_exist(mock_boto_client, "my-bucket", "my-key")
    mock_boto_client.head_object.assert_called_once_with(Bucket="my-bucket", Key="my-key")
    assert result is True


def test_is_file_exist_false_404():
    mock_boto_client = MagicMock()
    # Simulate 404 error
    error_response = {"Error": {"Code": "404"}}
    mock_boto_client.head_object.side_effect = botocore.exceptions.ClientError(error_response, "HeadObject")

    result = is_file_exist(mock_boto_client, "my-bucket", "my-key")
    assert result is False


def test_is_file_exist_false_other_error():
    mock_boto_client = MagicMock()
    # Simulate other error (e.g., 500)
    error_response = {"Error": {"Code": "500"}}
    mock_boto_client.head_object.side_effect = botocore.exceptions.ClientError(error_response, "HeadObject")

    result = is_file_exist(mock_boto_client, "my-bucket", "my-key")
    assert result is False
