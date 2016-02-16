#!/usr/bin/python3

import socket
import gzip
from struct import Struct
from random import randint

alfred_tlv = Struct("!BBH")
# type
# version
# length

alfred_request_v0 = Struct("!%isBH" % alfred_tlv.size)
# (alfred_tlv) header
# requested_type
# tx_id

alfred_transaction_mgmt = Struct("!HH")
# id
# seqno

ETH_ALEN = 6
mac_address = Struct("!%iB" % ETH_ALEN)

alfred_data = Struct("!%is%is" % (ETH_ALEN, alfred_tlv.size))
# (mac_address) source
# (alfred_tlv) header
# data[0]

alfred_push_data_v0 = Struct("!%is%is" % (alfred_tlv.size, alfred_transaction_mgmt.size))
# (alfred_tlv) header
# (alfred_transaction_mgmt) txm
# (alfred_data) data[0]

class AlfredPacketType(object):
	ALFRED_PUSH_DATA = 0
	ALFRED_ANNOUNCE_MASTER = 1
	ALFRED_REQUEST = 2
	ALFRED_STATUS_TXEND = 3
	ALFRED_STATUS_ERROR = 4

ALFRED_VERSION = 0


class AlfredConnection(object):
	def __init__(self, socket="/var/run/alfred.sock"):
		self.socket = socket

	def _get_alfred_socket(self):
		client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
		client.connect(self.socket)
		return client

	def send(self, data_type, data, mac=None):
		"""
		Args:
			data_type (int): Number between 1 and 255 (1-63 are reserved)
			data (string): Unicode String
		
		Optional Args:
			mac (string): Alfred server will use local mac if not set
		"""
		client = self._get_alfred_socket()

		if mac:
			mac = [int(i, 16) for i in mac.strip().split(":")]
		else:
			# ALFRED server will fill this field
			mac = [0] * ETH_ALEN

		data = data.encode("UTF-8")
		data_tlv = alfred_tlv.pack(data_type, ALFRED_VERSION, len(data))
		source = mac_address.pack([0]*ETH_ALEN)
		pkt_data = alfred_data.pack(source, data_tlv) + data

		request_id = randint(0, 65535)
		seq_id = 0
		txm = alfred_transaction_mgmt.pack(request_id, seq_id)
		tlv = alfred_tlv.pack(AlfredPacketType.ALFRED_PUSH_DATA, ALFRED_VERSION, len(pkt_data) + len(txm))
		pkt_push_data = alfred_push_data_v0.pack(tlv, txm) + pkt_data

		client.send(pkt_push_data)
		client.close()

	def fetch(self, data_type):
		"""
		Fetches data from alfred server (tries gzip decompress) and converts the data into
		a unicode string (assuming UTF-8 encoding).

		Args:
			data_type (int): Number between 1 and 255 (1-63 are reserved)

		Returns:
			dict: mac (string) -> data (string)
		"""
		client = self._get_alfred_socket()

		header = alfred_tlv.pack(AlfredPacketType.ALFRED_REQUEST, ALFRED_VERSION, alfred_request_v0.size - alfred_tlv.size)
		request_id = randint(0, 65535)
		request = alfred_request_v0.pack(header, data_type, request_id)

		client.send(request)

		response = {}

		last_seq_id = -1
		while True:
			tlv = client.recv(alfred_tlv.size)
			if len(tlv) < alfred_tlv.size:
				# no (more) data available
				break
			assert len(tlv) == alfred_tlv.size

			res_type, res_version, res_length = alfred_tlv.unpack(tlv)
			assert res_type == AlfredPacketType.ALFRED_PUSH_DATA
			assert res_version == ALFRED_VERSION

			push = tlv + client.recv(alfred_push_data_v0.size - alfred_tlv.size)
			assert len(push) == alfred_push_data_v0.size
			res_length -= (alfred_push_data_v0.size - alfred_tlv.size)

			# check transaction_id and sequence_id
			tlv, txm = alfred_push_data_v0.unpack(push)
			trx_id, seq_id = alfred_transaction_mgmt.unpack(txm)
			assert seq_id > last_seq_id
			last_seq_id = seq_id
			assert trx_id == request_id

			while res_length > 0:
				data = client.recv(alfred_data.size)
				assert len(data) == alfred_data.size
				res_length -= alfred_data.size

				source, data_tlv = alfred_data.unpack(data)

				mac = ":".join(["%02x" % i for i in mac_address.unpack(source)])

				data_type_recv, data_version, data_length = alfred_tlv.unpack(data_tlv)
				assert data_type == data_type_recv

				payload = client.recv(data_length)
				assert len(payload) == data_length
				res_length -= data_length

				try:
					payload = gzip.decompress(payload)
				except:
					pass

				# decode string (expect UTF-8)
				payload = payload.decode("UTF-8", errors="replace")

				if mac in response:
					response[mac] += payload
				else:
					response[mac] = payload

		client.close()
		return response
