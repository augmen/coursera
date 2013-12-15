coursera-dl
===========

Coursera-dl is a python package for downloading course videos and resources
available at www.coursera.org.

Installation
------------

Make sure you have installed [Python][] and [pip][].

Then simply run: `pip install coursera-dl`

Depending on your setup this will create a `coursera-dl` script in `/usr/local/bin` (linux) or
`c:\\Python2.7\\Scripts` (windows)

(to upgrade use `pip install --upgrade`)

Usage
-----

See: `coursera-dl -h`

Example usage:

<pre>
coursera-dl ml-2012-002 -u myusername -p mypassword -d /my/coursera/courses/ algo-2012-001
</pre>

Note: you can also specify your login and password in `.netrc` file in your home directory.
Just add this line to `~/.netrc`
<pre>
machine coursera-dl login myusername password mypassword
</pre>

Now you can use coursera-dl like this:

<pre>
coursera-dl ml-2012-002 -n -d /my/coursera/courses/ algo-2012-001
</pre>

Note: ensure you have accepted the honor code of the class before using
this script (happens the very first time you go to the class page).

  [Python]: http://www.python.org/download/
  [pip]: http://www.pip-installer.org/en/latest/installing.html
