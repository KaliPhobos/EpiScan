# Please read the disclaimer below


# Basics
A brief introduction to what **EpiScan** is and how to use it.

### What is EpiScan
**EpiScan** is a small tool designed to help people with **photosensitive epilepsy** by scanning large video files (movies) within minutes and providing confirmation whether the video can be safely viewed.

### How it works
EpiScan analyzes each frame of the given video separately, checks for changes in overall brightness, and detects flashy scenes known to trigger seizures in photosensitive epilepsy patients.\
Results are presented in an easy-to-understand graph that highlights problematic scenes, giving users a suitable basis for deciding whether a movie/series is good to watch.

Currently, three different analysis modes are available (or rather "being worked on" ^^):
- **Absolute Brightness**: If the movie was black and white, how bad would the flickering be?
- **Absolute Brightness**: Same, but using D. Finley's formula (alienryderflex.com/hsp.html)*.
- **Channels for R, G, and B** are analyzed separately for their individual brightness changes.

Each analysis method is then stacked over a variable number of frames to detect longer episodes of flashing (which are much more important than sudden cuts to brighter/darker scenes)
```
* The HSP formula used by D. Finley is.
Brightness = sqrt( .299 R^2 + .587 G^2 + .114 B^2 )
Read all about it at http://alienryderflex.com/hsp.html
```

### Roadmap
What to expect from this tool in the long run
- Catalog of already scanned movies (probably community-driven?)
- Actual scores based upon said catalog
- Preview function for detected conspicuous scenes for manual review (by partners/friends obviously!)
- Correct handling of whole series over several seasons/episodes
- Appropriate readme

# DISCLAIMER
This tool is primarily intended for partners and friends of people with photosensitive epilepsy to help them get better results in checking whether a movie is appropriate for their friend/partner.
Although it is an improvement over just skipping through a movie to see if it contains a problematic level of flashy scenes, **I cannot guarantee** the validity of results.

Photosensitive epilepsy is different for everyone. What is a guaranteed seizure for one patient may not be a problem for another - and vice versa!

Also EpiScan has (and will always have) problems to detect certain types of flashes, especially (but not only!) local flashes that do not cause large brightness changes (think laser guns and static noise).

So please, PLEASE, consider any results from this tool as a nice first guess - but nothing more!

You remember there's a flashy scene in a movie which you wish to skip, but you can't remember where in the movie? Let EpiScan help you.\
Going for an unfamiliar movie and have no one nearby to help in an emergency? Probably it's better not to rely on EpiScan....
