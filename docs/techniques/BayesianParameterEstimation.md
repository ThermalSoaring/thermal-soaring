# Bayesian Parameter Estimation

## What is it?
The idea behind Bayesian parameter estimation is figuring out what is the most
likely values of each of a model's parameters.

For example, if you have a simple symmetric Gaussian-shaped thermal
model, then the parameters are the position of the thermal center, the
maximum upward velocity, and how quickly the velocity falls off going
away from the center.

Or, if you have a certain function such as _y=a\*exp(b\*x)+c_, then you
could figure out the best estimates for the parameters _a_, _b_, and _c_
if you have _(x,y)_ data.

## How can you use it?
If you're using Python, then there is a nice library called
[PyMC3](https://github.com/pymc-devs/pymc3) that has lots of great
[tutorials and examples](http://pymc-devs.github.io/pymc3/). This is for
Python 3. If you're using Python 2, then there is [an older
version](https://github.com/pymc-devs/pymc) that works. For our project,
I used PyMC3.

Here is an example with PyMC3 fitting the function _V(t) =
V\_0\*(1-exp(-t/tau))_ that I used in a Physical Electronics lab.

	import random
	import numpy as np
	import pymc3 as pm
	import scipy as sp
	import theano
	import theano.tensor as t
	import pandas as pd
	import seaborn as sns
	from scipy.stats import kde
	import matplotlib.pyplot as plt
	from pandas.tools.plotting import andrews_curves

	# Make them look prettier
	plt.style.use('ggplot')
	sns.set(style="ticks")

	# To display plots in Jupyter, uncomment
	#%matplotlib inline

	# For reproducibility
	random.seed(126)
	np.random.seed(123)

	# Input data
	#data = ... Load data ...
	t = np.array(data[['Second']])
	v = np.array(data[['Volt']])

	# Perform regression
	def VoltageEq(t, V0, tau):
		# We're not performing regression on the time inputs, just on the parameters
		# of our model, so pass in the same t no matter what
		def V(V0, tau):
			# Note we're using pm.exp not np.exp or math.exp
			return V0*(1-pm.exp(-t/tau))
		
		return V(V0, tau)

	# With normal priors
	with pm.Model() as model:
		# Priors
		# See: http://stackoverflow.com/q/25342899
		V0 = pm.Normal('V0', mu=0, sd=100)
		tau = pm.Normal('tau', mu=0, sd=100)
		
		# Our equation we're trying to estimate the parameters of, but with the time
		# values plugged in already
		veq = VoltageEq(t, V0, tau)
		
		# Observe the voltages
		V = pm.Normal('V', mu=veq, observed=v)

		# Sample this to find the posterior, note Metropolis works with discrete
		step = pm.Metropolis()
		start = pm.find_MAP(fmin=sp.optimize.fmin_powell)
		trace = pm.sample(10000, step=step, progressbar=True, start=start)
		pm.traceplot(trace, ['V0', 'tau'])
		plt.show()
		pm.summary(trace, ['V0', 'tau'], roundto=10)

## Details
[A very practical online
book](http://nbviewer.jupyter.org/github/CamDavidsonPilon/Probabilistic-Programming-and-Bayesian-Methods-for-Hackers/tree/master/)
(i.e., shows the code and not just describing the theory) that uses PyMC2

[PyMC3 Tutorials and Examples](http://pymc-devs.github.io/pymc3/)

[PyMC3 Github](https://github.com/pymc-devs/pymc3)

[Bayesian machine
learning](https://www.metacademy.org/roadmaps/rgrosse/bayesian_machine_learning),
great online overview of many machine learning topics and how they relate

**Books**  
Bayesian Artificial Intelligence, 2nd Ed., by Kevin B. Korb and Ann E. Nicholson  
Learning Bayesian Networks, by Richard E. Neapolitan  
