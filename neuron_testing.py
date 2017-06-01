import nest
import nest.topology as topp
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import time

###########################################
####   PARAMETERS   #######################
###########################################

start_time = time.time()

freq_num = 25 # number of auditory frequencies
sample_size = 15 # number of neurons to record from
amp_factor = 100 # strength of signal coming from generators
sim_time = 200.0 # duration of simulation (ms)
grid_size = [5.0,5.0] # side lengths of topological layers (nm)

base_stim_rate = 2000.0 # stimulus rate (Hz)
tuning_rad = 5 # broadness of tuning curve

neuron_mod = 'iaf_psc_alpha'

stim_layer_param = {
	'extent'   : grid_size,  # size of layer (nm^2)
	'rows'     : amp_factor, # strength of signal amplification
	'columns'  : freq_num,   # one column per frequency
	'elements' : 'poisson_generator'
}
pyr_layer_param = {
	'extent'   : grid_size, # size of layer (nm^2)
	'rows'     : 500,       # relative number of neurons per frequency
	'columns'  : freq_num,  # one column per frequency
	'elements' : neuron_mod
}
inh_layer_param = {
	'extent'   : grid_size, # size of layer (nm^2)
	'rows'     : 50,        # relative number of neurons per frequency
	'columns'  : freq_num,  # one column per frequency
	'elements' : neuron_mod
}
stim_conn_param = {
	'connection_type': 'divergent', # connection based on target layer
	'mask': {'circular': {'radius': grid_size[0]/4}},
	'kernel': {'gaussian': { # connection probability based on distance
		'p_center': 1.0,
		'sigma': 0.5
	}},
	'weights': {'gaussian': { # weight of connection based on distance
		'p_center': 10.0,
		'sigma': 1.0,
		'min': 0.0
	}}
}
pyr_conn_param = {
	'connection_type': 'divergent', # connection based on target layer
	'mask': {'circular': {'radius': grid_size[0]/2}},
	'kernel': {'gaussian': { # connection probability based on distance
		'p_center': 1.0,
		'sigma': 2.0
	}},
	'weights': {'gaussian': { # weight of connection based on distance
		'p_center': 1.5,
		'sigma': 1.0,
		'min': 0.0
	}}
}
inh_conn_param = {
	'connection_type': 'divergent', # connection based on target layer
	'mask': {'circular': {'radius': grid_size[0]/4}},
	'kernel': {'gaussian': { # connection probability based on distance
		'p_center': 1.0,
		'sigma': 1.0
	}},
	'weights': {'gaussian': { # weight of connection based on distance
		'p_center': -1.5,
		'sigma': 1.0,
		'max': 0.0
	}}
}

np.random.seed(10) # set numpy seed for reproducability
nest.ResetKernel() # reset NEST
nest.SetKernelStatus({'local_num_threads': 4}) # threading for efficiency

###########################################
####   DISPLAY FUNCTIONS   ################
###########################################

# Convert raw integers to corresponding frequencies
def freq_convert(x):
	return 1000*(x+1)/6+334

# Resize variables for printing to terminal window
def clip_print(item,clip_size,clip_fill):
	curr_size = len(str(item))
	if curr_size >= clip_size:
		return item
	else:
		return str(clip_fill) * (clip_size - curr_size) + str(item)

# Print to terminal window live updates with simulation information
def live_update(x):
	tot_runtime = time.time()-start_time
	sim_runtime = time.time()-sim_start_time
	if x == 0:
		est_wait = '~'
	else:
		est_wait = int((freq_num*sim_runtime/x-sim_runtime)/60+0.5)
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
	print "XXX   WORKING ON SIMULATION %s of %s   XXX" \
		% (clip_print(x+1,2,'0'), clip_print(freq_num,2,'0'))
	print "XXX      %s MINUTES HAVE PASSED       XXX" \
		% clip_print(int(tot_runtime/60),3,' ')
	print "XXX   %s MINUTES REMAINING (APPROX)   XXX" \
		% (clip_print(est_wait,3,' '))
	print "XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

###########################################
####   NETWORK SETUP   ####################
###########################################

# Create layers
layers = {
	'stim': topp.CreateLayer(stim_layer_param),
	'pyr' : topp.CreateLayer(pyr_layer_param),
	'inh' : topp.CreateLayer(inh_layer_param)
}

# Connect layers
topp.ConnectLayers(layers['stim'], layers['pyr'], stim_conn_param)
topp.ConnectLayers(layers['pyr'], layers['inh'], pyr_conn_param)
topp.ConnectLayers(layers['inh'], layers['pyr'], inh_conn_param)

# Connect spike detectors to random recording neurons
spk_det = {
	'pyr': nest.Create('spike_detector'),
	'inh': nest.Create('spike_detector')
}
rec_neurons = {
	'pyr': np.random.choice(nest.GetNodes(layers['pyr'])[0],
	                        size=sample_size, replace=False).tolist(),
	'inh': np.random.choice(nest.GetNodes(layers['inh'])[0],
	                       size=sample_size, replace=False).tolist()
}
for n in rec_neurons.keys():
	rec_neurons[n].sort()
	nest.Connect(rec_neurons[n], spk_det[n])

###########################################
####   SIMULATION   #######################
###########################################

# Initialize dictionary of firing rates
firing_rates = {
	'pyr': [[] for i in range(sample_size)],
	'inh': [[] for i in range(sample_size)]
}

sim_start_time = time.time()

for freq in range(freq_num):
	nest.ResetNetwork()
	nest.SetKernelStatus({'time': 0.0})
	live_update(freq)
	
	# Set rate for stim_layer neurons based on frequency of stimulus
	for row in range(amp_factor):
		for col in range(max(0,freq-tuning_rad),
			             min(freq_num,freq+tuning_rad+1)):
			rate_factor = max(0.0,(tuning_rad-abs(freq-col))/float(tuning_rad))
			nest.SetStatus(topp.GetElement(layers['stim'],[col,row]),
				           {'rate': rate_factor*base_stim_rate})
	
	# Simulate and record event data from spike detectors
	nest.Simulate(sim_time)
	
	# Store firing rate data for each set of neurons
	for n in rec_neurons.keys():
		sender_fires = [0] * sample_size
		for neuron_id in nest.GetStatus(spk_det[n])[0]['events']['senders']:
			sender_fires[rec_neurons[n].index(neuron_id)] += 1
		for j in range(sample_size):
			firing_rates[n][j].append(1000*sender_fires[j]/sim_time)
	
	# Reset rates for stim_layer neurons
	for row in range(amp_factor):
		for col in range(max(0,freq-tuning_rad),
			             min(freq_num,freq+tuning_rad+1)):
			nest.SetStatus(topp.GetElement(layers['stim'],[col,row]),
				           {'rate': 0.0})

###########################################
####   CALCULATIONS   #####################
###########################################

# Normalize and average firing rates for each set of neurons
avg_fr_rates = {}
for n in firing_rates.keys():

	# Normalize firing rates between 0.0 and 1.0
	norm_fr_rates = []
	for frs in firing_rates[n]:
		normalized = []
		max_fr = max(frs)
		for fr in frs:
			normalized.append(fr/max_fr)
		norm_fr_rates.append(normalized)
	
	# Shift firing rate data to be centered
	shift_fr_rates = [[] for i in range(2*freq_num-1)]
	for i in range(sample_size):
		peak = norm_fr_rates[i].index(1.0)
		for j in range(freq_num):
			shift_fr_rates[j+freq_num-peak-1].append(norm_fr_rates[i][j])
	
	# Create a single averaged list of firing rates for each set of neurons
	avg_fr_rates[n] = [np.mean(i) for i in shift_fr_rates]

###########################################
####   GRAPHS   ###########################
###########################################

for figure in range(2):
	plt.figure(figure)
	
	if figure == 0: # graph of all recorded firing rates
		fr_dict = firing_rates
		plt.gca().set_xlim(freq_convert(0),freq_convert(freq_num-1))
	else: # normalized graph of firing rates for each set of neurons
		fr_dict = avg_fr_rates
		plt.gca().set_xlim(-1*freq_num+1,freq_num)
	
	# Basic plot setup
	plt.subplots_adjust(wspace=0.3,hspace=0.6)
	plt.gcf().set_size_inches(12,10,forward=True)
	plt.title("Firing Rate v Frequency")
	plt.xlabel('frequency (Hz)')
	plt.ylabel('firing rate (spikes/sec)')
	pyr_lab = mlines.Line2D([],[],color='blue',label='pyramidal')
	inh_lab = mlines.Line2D([],[],color='red',label='inhibitory')
	plt.legend(handles=[pyr_lab,inh_lab])
	
	# Plot separate tuning curve data for pyramidal and inhibitory neurons
	for n in firing_rates.keys():
		if n == 'pyr':
			plt_sty = 'b-'
		else:
			plt_sty = 'r-'
		if figure == 0:
			for j in range(sample_size):
				x_axis = [freq_convert(k) for k in range(freq_num)]
				y_axis = fr_dict[n][j]
				plt.plot(x_axis, y_axis, plt_sty)
		else:
			x_axis = [i for i in range(-1*freq_num+1,freq_num)]
			y_axis = fr_dict[n]
			plt.plot(x_axis, y_axis, plt_sty)

# Final display of runtime
print "TOTAL SIMULATION RUNTIME: %s MINUTES" \
	% str(int((time.time()-start_time))/60)
plt.show()