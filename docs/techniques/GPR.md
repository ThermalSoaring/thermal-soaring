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
This is the library that was used in our project. Other possibilities for
Python are [GPy](https://github.com/SheffieldML/GPy) and
[GPflow](https://github.com/GPflow/GPflow).

There's this parameter caled a "nugget" that you will have to set.
Basically, the larger this value, the more smooth your output will be.
The smaller it is, the closer it will match your input data. There are
two reasons this should be non-zero:

* _Measurement error._ Back in Principles of Physics, you may remember
  coming up with estimates of uncertainty for all your measurements and
  then propagating that error through your calculations. By setting a
  higher nugget, you can show that your input data has some measurement
  error in it.
* _Numerical issues._ Even if you have no measurement error, you may get
  really bizarre results if you set the nugget too low due to numerical
  issues in inverting matrices. By having a non-zero nugget, it can
  handle these numerical issues.

Now, if you look at the theory of GPR, you'll notice that there are
hyperparameters. However, scikit-learn can estimate these for you using
maximum-likelihood estimation (MLE). You have two options:

* _Let scikit-learn estimate these with MLE._ In this case, _theta0_ is the
  starting estimate of these parameters. Set _thetaL_ and _thetaU_ to be the
  upper and lower bounds on the guesses of parameters used in MLE. If these are
  set, it will estimate the hyperparameters. After running GPR, you can find
  out what the estimates of the parameters were by looking at the
  _theta\__ member variable.
* _Set the hyperparameters._ If you come up with the estimates in another
  way, then do not set _thetaL_ or _thetaU_ and specify all your
  parameters in _theta0_.

The scikit-learn documentation is very good, so for more details look there.

## Details
If you want a thorough about GPR, then check out this book that is available
online:

[Gaussian Processes for Machine Learning, by Rasmussen and
Williams](http://www.gaussianprocess.org/gpml/chapters/RW.pdf)
