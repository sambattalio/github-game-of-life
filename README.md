# github-game-of-life
My attempt to make GitHub commit calendar into a working game of life simulation

Runs on my [alt account](https://github.com/sambattalio-gol)

Hopefully over the next year+ it will run the game of life oscillator right!

# Current Screenshot

Using selenium and s3, I am able to update this screenshot daily! So stay tuned.

(The first week of running is August, so the contributions before are not a part of the "game")
 
# How it works

I utilize [aws-chalice](https://github.com/aws/chalice) to create a pretty straight forward lambda function that runs on a Cloudwatch Schedule (cronjob). I have hard-coded in an oscilator that runs like below(but tilted 90 degrees): 

https://upload.wikimedia.org/wikipedia/commons/1/12/Game_of_life_toad.gif


# Artists rendering of what should appear

[here](https://chadpaste.com/f/btq.png)
