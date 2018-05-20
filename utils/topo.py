import json

# use adjacency list for representing network would be intuitive for human
class topo:
	def __init__(self):
		self.graph=[]

	@staticmethod
	def read_from_json(filename):
		raw=open(filename).read()
		jdata=json.loads(raw)
		nodes=[]
		# init graph based on how many nodes we have
		node_count=len(jdata)
		for i in range(0, node_count):
			nodes.append(jdata[i])
		return nodes

	@staticmethod
	def set_graph(self, graph):
		self.graph=graph

	# only should be called after nodes are inited
	#def generate_graph(self):
	#	for node in self.nodes:
	#		nid=node['id']

def test():
	test_topo=topo.read_from_json('two_subnet.topo')
	print test_topo.nodes[0]['name']
