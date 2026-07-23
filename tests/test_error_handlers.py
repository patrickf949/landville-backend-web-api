from rest_framework.test import APITestCase
from rest_framework import status
from django.utils.encoding import force_str


class TestErrorHandler(APITestCase):
    """
    This class define test for error 404 handler
    Methods
    -------
    test_handler_not_found_error()
        test if a custom error message is send when the url is not  found
    """

    def test_handler_not_found_error(self):
        """
        Test if a json response is returned when an endpoint is not found
        """
        response = self.client.get('/not-found-page/')
        message = ("The endpoint you are trying to access might "
                   "have been removed, "
                   "had its name changed, or is temporarily unavailable. "
                   "Please check the documentation here : "
                   "/api/v1/documentation/ "
                   "and try again later.")
        self.assertEqual(response.json().get('message'), message)
        self.assertJSONEqual(force_str(response.content),
                             {'message': message})
        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND)
