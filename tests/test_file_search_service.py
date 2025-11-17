import unittest
from code.file_search_service import (
    UploadResult,
    document_exists,
    get_or_create_store,
    upload_single_file,
)
from unittest.mock import MagicMock, mock_open, patch


class TestFileSearchService(unittest.TestCase):

    @patch("google.genai.Client")
    def test_get_or_create_store_exists(self, MockClient):
        # Arrange
        mock_client_instance = MockClient()
        mock_store = MagicMock()
        mock_store.display_name = "existing_store"
        mock_store.name = "fileSearchStores/existing_store_123"
        mock_client_instance.file_search_stores.list.return_value = [mock_store]

        # Act
        store_name = get_or_create_store(mock_client_instance, "existing_store")

        # Assert
        self.assertEqual(store_name, "fileSearchStores/existing_store_123")
        mock_client_instance.file_search_stores.create.assert_not_called()

    @patch("google.genai.Client")
    def test_get_or_create_store_creates_new(self, MockClient):
        # Arrange
        mock_client_instance = MockClient()
        mock_client_instance.file_search_stores.list.return_value = []
        mock_created_store = MagicMock()
        mock_created_store.name = "fileSearchStores/new_store_456"
        mock_client_instance.file_search_stores.create.return_value = mock_created_store

        # Act
        store_name = get_or_create_store(mock_client_instance, "new_store")

        # Assert
        self.assertEqual(store_name, "fileSearchStores/new_store_456")
        mock_client_instance.file_search_stores.create.assert_called_once_with(
            config={"display_name": "new_store"}
        )

    @patch("google.genai.Client")
    def test_document_exists(self, MockClient):
        # Arrange
        mock_client_instance = MockClient()
        mock_doc = MagicMock()
        mock_doc.display_name = "existing_doc.pdf"
        mock_doc.name = "fileSearchStores/store/documents/doc1"
        mock_doc.state = "ACTIVE"
        mock_client_instance.file_search_stores.documents.list.return_value = [mock_doc]

        # Act
        result = document_exists(mock_client_instance, "store_name", "existing_doc.pdf")

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(result.display_name, "existing_doc.pdf")

    @patch("google.genai.Client")
    def test_document_does_not_exist(self, MockClient):
        # Arrange
        mock_client_instance = MockClient()
        mock_client_instance.file_search_stores.documents.list.return_value = []

        # Act
        result = document_exists(
            mock_client_instance, "store_name", "non_existing_doc.pdf"
        )

        # Assert
        self.assertIsNone(result)

    @patch("code.file_search_service.tempfile.NamedTemporaryFile")
    @patch("google.genai.Client")
    def test_upload_single_file_success(self, MockClient, MockNamedTemporaryFile):
        # Arrange
        mock_client_instance = MockClient()
        mock_uploaded_file = MagicMock()
        mock_uploaded_file.name = "test.pdf"
        mock_uploaded_file.type = "application/pdf"
        mock_uploaded_file.getvalue.return_value = b"file content"

        # Mock the temporary file
        mock_tmp_file = MagicMock()
        mock_tmp_file.__enter__.return_value.name = "/tmp/test.pdf"
        MockNamedTemporaryFile.return_value = mock_tmp_file

        # Mock the API operation
        mock_operation = MagicMock()
        mock_operation.name = "operations/123"
        mock_operation.done = True
        mock_operation.error = None
        mock_response = MagicMock()
        mock_response.document_name = "stores/store/documents/doc1"
        mock_operation.response = mock_response

        mock_document = MagicMock()
        mock_document.state = "ACTIVE"

        mock_client_instance.file_search_stores.upload_to_file_search_store.return_value = (
            mock_operation
        )
        mock_client_instance.operations.get.return_value = mock_operation
        mock_client_instance.file_search_stores.documents.get.return_value = (
            mock_document
        )

        # Act
        with patch("builtins.open", mock_open(read_data=b"file content")):
            result = upload_single_file(
                mock_client_instance, "store_name", mock_uploaded_file
            )

        # Assert
        self.assertTrue(result.success)
        self.assertEqual(result.file_name, "test.pdf")


if __name__ == "__main__":
    unittest.main()
