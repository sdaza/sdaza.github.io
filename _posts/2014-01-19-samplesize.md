---
layout: post
title: "Functions for sample size and error"
author: Sebastian Daza
date: 2014-01-19
giscus_comments: true
tags: 
  - R 
  - survey
---


Here I show two functions in R to define sample sizes and errors of a proportion, taking into account design effect, response rate, finite population correction, and stratification. They are useful when one needs to do these calculations quickly.

**Note: I created a package with similar functions. [See here](/blog/2015/sampler/).**

The inputs are:

- **n** = sample size
- **e** = sampling error
- **deff** = design effect, by default 1 (SRS)
- **rr** = response rate, by default 1
- **N** = population size, by default NULL (infinite population)
- **cl** = confidence level , by default .95
- **p** = proportion, by default 0.5 (maximum variance of a proportion)
- **relative** = to estimate relative error, by default FALSE

## first, load the functions




{% highlight r %}
library(devtools); source_gist("7896840")
{% endhighlight %}

## serr: sampling error

An example for n = 400 and all inputs at their default values:


{% highlight r %}
serr(400)
{% endhighlight %}



{% highlight text %}
## [1] 0.049
{% endhighlight %}

The output is rounded to 4 decimals. A more complete example:

- **n** = 400
- **deff** = 1.5
- **response rate** = 80%
- **population size** = 1000


{% highlight r %}
serr(n=400, deff=1.5, rr=.8, N=1000)
{% endhighlight %}



{% highlight text %}
## [1] 0.0595
{% endhighlight %}

The sample size (n) has always to be lower than the population (N).  It is important to note that the final sample size used to compute the sampling error is:

$$ n = \frac{N}{deff} * rr$$


{% highlight r %}
serr(n=400, N=350)
{% endhighlight %}



{% highlight text %}
## Error: n is bigger than N
{% endhighlight %}

## ssize: sample size

Let's get a sample size with an error of .03, a population of 1000 elements, a response rate of 0.80, and an effect design of 1.2:


{% highlight r %}
ssize(e=.03, deff=1.2, rr=.8, N=1000)
{% endhighlight %}



{% highlight text %}
## [1] 775
{% endhighlight %}

If the the sample size is bigger than the population because of low response rates or big design effects, the sample size will be fixed to N:


{% highlight r %}
ssize(e=.03, deff=5, rr=.6, N=1000)
{% endhighlight %}



{% highlight text %}
## n is bigger than N in some rows: n = N
{% endhighlight %}



{% highlight text %}
## [1] 1000
{% endhighlight %}

## Working with strata

Finally, we can estimate different sample sizes by strata using vectors or a data frame:


{% highlight r %}
# example sampling frame (4 strata)
frame <- data.frame(
	strata = 1:4,
	N =c(10000, 5000, 2000, 1000),
	deff =c(1.1, 1, 1.3, .8),
	rr = c(.8, .9, .85,.8),
	p = c(.3, .6, .1, .2))
{% endhighlight %}


{% highlight text %}
##   strata     N deff   rr   p
## 1      1 10000  1.1 0.80 0.3
## 2      2  5000  1.0 0.90 0.6
## 3      3  2000  1.3 0.85 0.1
## 4      4  1000  0.8 0.80 0.2
{% endhighlight %}


{% highlight r %}
frame$n1 <- ssize(e=.02, deff=frame$deff, rr=frame$rr, N=frame$N, p=frame$p)
frame$e1 <- serr(n=frame$n1, deff=frame$deff, rr=frame$rr, N=frame$N, p=frame$p)
{% endhighlight %}


{% highlight text %}
##   strata     N deff   rr   p   n1   e1
## 1      1 10000  1.1 0.80 0.3 2308 0.02
## 2      2  5000  1.0 0.90 0.6 1753 0.02
## 3      3  2000  1.3 0.85 0.1  923 0.02
## 4      4  1000  0.8 0.80 0.2  606 0.02
{% endhighlight %}

As easy as falling off a log!

