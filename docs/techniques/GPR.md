# Gaussian Process Regression (GPR)

## What is it?
This is function approximation. You give it inputs and it tries to predict what
the function looks like both at the locations you provided and at other
locations.

It is probabilistic, meaning that rather than just providing a single output
value at each position, it provides a probability distribution over values.
This probability distribution is Gaussian.

## How can you use it?
One Python library that provides GPR is
[scikit-learn](http://scikit-learn.org/stable/modules/gaussian_process.html).

## Details
If you want a thorough about GPR, then check out this book that is available
online:

[Gaussian Processes for Machine Learning, by Rasmussen and
Williams](http://www.gaussianprocess.org/gpml/chapters/RW.pdf)
