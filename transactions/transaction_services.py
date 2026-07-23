"""A module that provides services associated financial transactions"""
import os
import hashlib
import requests
import json
import datetime
import base64
from Cryptodome.Cipher import DES3
from urllib.parse import urljoin
from authentication.models import User


class TransactionServices:
    """A helper class for online payment services"""

    rave_public_key = os.getenv('RAVE_PUBLIC_KEY', '')
    rave_secret_key = os.getenv('RAVE_SECRET_KEY', '')
    redirect_url = os.getenv('RAVE_REDIRECT_URL', '')

    @classmethod
    def get_key(cls):
        """
        A function that uses the secret key to generate encryption key
        :return: encryption key
        """

        hashed_secret_key = hashlib.md5(
            cls.rave_secret_key.encode("utf-8")
        ).hexdigest()
        hashed_secret_key_last12 = hashed_secret_key[-12:]
        secret_key_adjusted = cls.rave_secret_key.replace('FLWSECK-', '')
        secret_key_adjusted_first12 = secret_key_adjusted[:12]
        return secret_key_adjusted_first12 + hashed_secret_key_last12

    @staticmethod
    def encrypt_data(key, plain_text):
        """
        This is the encryption function that encrypts your payload by
        passing the text and your encryption Key.
        :param key: str: DES3 encryption key
        :param plain_text: Dict: the payload to be encrypted before calling
        rave endpoint
        :return: Encrypted payload to send to rave endpoint
        """

        block_size = 8
        pad_diff = block_size - (len(plain_text) % block_size)
        cipher = DES3.new(key, DES3.MODE_ECB)
        plain_text = f'{plain_text}{"".join(chr(pad_diff) * pad_diff)}'
        test = plain_text.encode('utf-8')
        encrypted = base64.b64encode(cipher.encrypt(test)).decode('utf-8')
        return encrypted

    @classmethod
    def rave_call(cls, data):
        """
        A method that sends encrypted payment data to rave platform
        :param data: data encrypted with DES3
        :return: JSON response from rave endpoint
        """
        hashed_sec_key = cls.get_key()
        encrypt_3DES_key = cls.encrypt_data(hashed_sec_key, json.dumps(data))

        payload = {
            'client': encrypt_3DES_key
        }

        endpoint = urljoin(os.getenv('RAVE_URL', 'https://api.flutterwave.com/'),
                           'v3/charges?type=card')
        headers = {
            'content-type': 'application/json',
            'Authorization': f'Bearer {cls.rave_secret_key}'
        }
        response = requests.post(
            endpoint, headers=headers, data=json.dumps(payload))
        return response.json()

    @classmethod
    def initiate_card_payment(cls, pay_data):
        """
        A method that initiate card payment
        :param pay_data: dict: information about the card and user making
        payment. Rave uses this to determine if the payment is local or foreign
        :return: JSON response from rave endpoint
        """
        data = {
            'card_number': pay_data.get('cardno'),
            'cvv': pay_data.get('cvv'),
            'expiry_month': pay_data.get('expirymonth'),
            'expiry_year': pay_data.get('expiryyear'),
            'currency': 'NGN',
            'country': pay_data.get('country', 'NG'),
            'amount': pay_data.get('amount'),
            'email': pay_data.get('email'),
            'fullname': f"{pay_data.get('firstname', '')} {pay_data.get('lastname', '')}".strip() or pay_data.get('email'),
            'tx_ref': f'LANDVILLE-{datetime.datetime.now()}',
            'redirect_url': cls.redirect_url
        }

        return cls.rave_call(data)

    @classmethod
    def authenticate_card_payment(cls, pay_data):
        """
        A method that provide the needed authentication for payment.
        Payment with Nigerian local card is authenticated with card pin.
        Payment with international card is authenticated with the customer's
        billing address details . Customers can easily find these on their
        bank statements.
        :param pay_data: payment data
        :return: JSON response
        """

        data = {
            'card_number': pay_data.get('cardno'),
            'cvv': pay_data.get('cvv'),
            'expiry_month': pay_data.get('expirymonth'),
            'expiry_year': pay_data.get('expiryyear'),
            'currency': 'NGN',
            'country': pay_data.get('country', 'NG'),
            'amount': pay_data.get('amount'),
            'email': pay_data.get('email'),
            'fullname': f"{pay_data.get('firstname', '')} {pay_data.get('lastname', '')}".strip() or pay_data.get('email'),
            'tx_ref': f'LANDVILLE-{datetime.datetime.now()}',
            'redirect_url': TransactionServices.redirect_url,
            'meta': {
                'save_card': pay_data.get('save_card'),
                'purpose': pay_data.get('purpose'),
                'property_id': pay_data.get('property_id')
            }
        }

        if 'auth_dict' in pay_data:
            # v3 expects authorization object
            data['authorization'] = pay_data['auth_dict']

        return cls.rave_call(data)

    @classmethod
    def validate_card_payment(cls, flwref, otp):
        """
        A method that validates card payment.
        For Nigerian credit/debit cards, validation is done via OTP
        :param flwref: flutterwave
        :param otp: OTP send to the user to validate transaction
        :return: JSON response
        """
        data = {
            'flw_ref': flwref,
            'otp': otp
        }

        endpoint = urljoin(os.getenv('RAVE_URL', 'https://api.flutterwave.com/'),
                           'v3/validate-charge')
        headers = {
            'content-type': 'application/json',
            'Authorization': f'Bearer {cls.rave_secret_key}'
        }
        response = requests.post(
            endpoint, headers=headers, data=json.dumps(data))
        response_json = response.json()
        response_json['status_code'] = response.status_code
        return response_json

    @classmethod
    def verify_payment(cls, txref):
        """
        :param txref: the transaction reference number for the payment
        :return: AJSON response
        """
        endpoint = urljoin(os.getenv('RAVE_URL', 'https://api.flutterwave.com/'),
                           f'v3/transactions/verify_by_reference?tx_ref={txref}')
        headers = {
            'content-type': 'application/json',
            'Authorization': f'Bearer {cls.rave_secret_key}'
        }

        response = requests.get(endpoint, headers=headers)
        return response.json()

    @classmethod
    def save_card(cls, verify_resp):
        """
        The service method that handles persistence of the card token
        :param verify_resp: the object containing the response from payment
        verification
        :return: A message indicating success or otherwise of the operation
        """
        email = verify_resp.get('data', {}).get('customer', {}).get('email')
        
        # Safe extraction of meta fields
        meta = verify_resp.get('data', {}).get('meta', {})
        # v3 meta can be dict or list of dicts depending on endpoint
        save_card_val = 0
        if isinstance(meta, dict):
            save_card_val = meta.get('save_card', 0)
        elif isinstance(meta, list):
            for m in meta:
                if m.get('metaname') == 'save_card':
                    save_card_val = m.get('metavalue', 0)
                    break
        
        card_data = verify_resp.get('data', {}).get('card', {})
        card_number = card_data.get('last_4digits', card_data.get('last4digits'))
        embedtoken = card_data.get('token', '')
        card_brand = card_data.get('issuer', card_data.get('brand', ''))
        card_expiry = f"{card_data.get('expiry_month', card_data.get('expirymonth', ''))}/" \
            f"{card_data.get('expiry_year', card_data.get('expiryyear', ''))}"
            
        card_info = {
            'embedtoken': embedtoken,
            'card_number': f'*********{card_number}',
            'card_expiry': card_expiry,
            'card_brand': card_brand
        }

        if verify_resp.get('data', {}).get('status') == 'successful' \
                and str(save_card_val) in ['1', 'true', 'True']:
            try:
                user = User.active_objects.filter(email=email)
                user.update(card_info=card_info)
                message = '. Card details have been saved.'
            except:  # noqa
                message = '. Card details could not be saved. Try latter.'
            return message
        return ''

    @classmethod
    def pay_with_saved_card(cls, user, amount):
        """
        A service method for payment with card tokens
        :param user: The user making the payment
        :param amount: The amount to pay.
        :return: A JSON response
        """
        data = {
            'currency': 'NGN',
            'token': user.card_info.get('embedtoken'),
            'country': 'NG',
            'amount': amount,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'tx_ref': f'LANDVILLE-{datetime.datetime.now()}'
        }

        if data['token'] is None:
            return {
                'data': {
                    'status_code': 400,
                    'status': 'You do not have a saved card'
                }}
                
        endpoint = urljoin(os.getenv('RAVE_URL', 'https://api.flutterwave.com/'),
                           'v3/tokenized-charges')
        headers = {
            'content-type': 'application/json',
            'Authorization': f'Bearer {cls.rave_secret_key}'
        }

        response = requests.post(
            endpoint, headers=headers, data=json.dumps(data)).json()
        
        # Ensure status code is bundled for existing views
        if 'data' not in response:
            response['data'] = {}
        response['data']['status_code'] = 200 if response.get('status') == 'success' else 400
        return response
