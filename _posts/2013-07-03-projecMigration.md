---
layout: post
title: "Migration: forward survival method"
author: Sebastian Daza
date: 2013-07-03
comments: true
---


This is a question about estimating incoming and outgoing movements of population. I have data on enrollment at a small college in 2009 and 2010, and also the information on student-years enrolled before students drop out of the college ($_nL_x$). Each year 400 freshman enroll. What is the number of net transfers (incoming minus outgoing) between 2009 and 2010?

|     | 2009  | 2010 | $_nL_x$ |
|:--- | :--- | :--- | :--- |
| Freshman | 400 | 400  | 99 |
| Sophomore | 350 | 389  | 90 |
| Junior | 300 | 420 | 80 |
| Senior | 300 | 350  | 78 |
| Higher | 300 | 300  | 77 |

Basically, I have to estimate the "extra"  population observed during 2010 that doesn't come from enrollment (births) or mortality (drop-outs). That is, to project the 2009 population assuming that is closed to migration. Just looking at the table one can see that the population is growing due to transfers (mortality and births are constant).

First, I estimate the survival ratios:





{% highlight r %}
p2009 <- c(400, 350, 300, 300, 300)
p2010 <- c(400, 389, 420, 350, 300)
Lx <- c(99, 90, 80, 78, 77)
{% endhighlight %}



{% highlight r %}
# survival ratios
sr <- NA
for (i in 1:(length(Lx) - 1)) {
    sr[i] <- Lx[i + 1]/Lx[i]
}

# open-end interval
sr[length(sr)] <- Lx[5]/(Lx[4] + Lx[5])
{% endhighlight %}



{% highlight text %}
## [1] 0.909 0.889 0.975 0.497
{% endhighlight %}


Second, I define the matrix to do the projection:


{% highlight r %}
m <- matrix(0, 5, 5)

# The population of the first interval has always to be
# 400*99/100 (births are constant)
m[1, 1] <- 99/100
# Because the population of the first interval is 400 in
# 2009 I use this shortcut
s <- diag(4)
s <- s * sr
m[2:5, 1:4] <- s
m[5, 5] <- sr[4]
{% endhighlight %}


The result is not exactly a Leslie matrix because I don't have fertility rates in the first row.


{% highlight text %}
##       [,1]  [,2]  [,3]  [,4]  [,5]
## [1,] 0.990 0.000 0.000 0.000 0.000
## [2,] 0.909 0.000 0.000 0.000 0.000
## [3,] 0.000 0.889 0.000 0.000 0.000
## [4,] 0.000 0.000 0.975 0.000 0.000
## [5,] 0.000 0.000 0.000 0.497 0.497
{% endhighlight %}


Finally, I can project forward:


{% highlight r %}
proj2010 <- m %*% p2009
{% endhighlight %}



{% highlight text %}
##      [,1]
## [1,]  396
## [2,]  364
## [3,]  311
## [4,]  292
## [5,]  298
{% endhighlight %}


The number of net transfers would be the differences between the observed population in 2010, and the 2010 projected population assuming that it is closed to migration (no transfers).


{% highlight r %}
sum(p2010 - proj2010)
{% endhighlight %}



{% highlight text %}
## [1] 198
{% endhighlight %}


This was an example of the forward survival method to estimate migration.