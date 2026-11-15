---
layout: "post"
title: "How to animate SnapKit constraint changes (with UIView.animate(withDuration:))"
date: "2016-12-30 21:08:01 +0000"
permalink: "/how-to-animate-snapkit-constraint-changes-with/"
wordpress_id: 17
wordpress_guid: "https://www.diegopetrucci.it/blog/2016/12/30/how-to-animate-snapkit-constraint-changes-with/"
render_with_liquid: false
categories: ["Uncategorised"]
tags: []
display_title: "How to animate SnapKit constraint changes (with UIView.animate(withDuration:))"
---

I might be dumb, but I had to look *really hard* to find any info on how to animate SnapKit constraints. The solution is pretty simple, and I suppose it also applies to AutoLayout stuff, but I’ve never used AutoLayout programmatically though, so I don’t really know. I’ve always used Auto Layout with storyboards and then, at some point, jumped to writing everything programmatically with SnapKit (and I love it).

Anyway, let’s suppose you have a childView of your viewController.view, like so:

You want to animate a constraint change of the childView. You do it the standard way:

This is what I tried, but *it won’t work*. You usually put the code that needs to change in your UIView.animate(withDuration:) method and it works fine, but it won’t with constraint changes.

What you need to *actually* do:

It looked counter-intuitive to me, but you need to first write your constraint changes and then animate the layoutIfNeeded() method. Also, be sure to call layoutIfNeeded() to the superview of the view where the changes happen, in my case viewController.view.
