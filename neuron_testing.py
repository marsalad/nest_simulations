import nest
import matplotlib.pyplot as plt
import nest.voltage_trace

###########################################
####   PARAMETERS   #######################
###########################################

nest.ResetKernel()

neuron_mod = 'iaf_psc_exp'
neuron_param = {
	'E_L'     : -70.0, # resting membrane potential (mV)
	'V_reset' : -70.0, # reset membrane potential after spiking (mV)
	'V_th'    : -55.0, # spike threshold (mV)
	'tau_m'   : 10.0   # membrane time constant (ms)
}
stim_param = {
	'rate': 2000.0 # firing rate (Hz)
}
freq_num = 4 # number of stimuli frequencies
neuron_num = 6 # number of downstream neurons

###########################################
####   CONNECTIONS   ######################
###########################################

# Generate stimulus, send identical spike trains to target neurons
stim = nest.Create('parrot_neuron')
nest.Connect(nest.Create('poisson_generator', params=stim_param),stim)

# Create tonotopic map of frequencies
tono_map = nest.Create(neuron_mod, freq_num, neuron_param)
neurons = nest.Create(neuron_mod, neuron_num, neuron_param)

# Connect tonotopic map to downstream neurons
for i in range(len(tono_map)):
	nest.Connect(tono_map[i:i+1],neurons[i:i+3], syn_spec={'weight':1000.0})

# Create and connect devices
volt_mtr = nest.Create('voltmeter')
spk_det = nest.Create('spike_detector')
nest.Connect(volt_mtr, neurons)
nest.Connect(neurons, spk_det)
nest.Connect(stim, tono_map, syn_spec={'weight': 100.0})

###########################################
####   SIMULATION   #######################
###########################################

nest.Simulate(500)

###########################################
####   PLOTTING   #########################
###########################################

# Plot membrane potential and spike trains
plt.subplot(211)
nest.voltage_trace.from_device(volt_mtr)
plt.subplot(212)
events = nest.GetStatus(spk_det)[0]['events']
plt.plot(events['times'],events['senders'], 'o')
plt.show()