# Donuts with Voyager

Initial scribbles to have an event driven version of donuts

# Installation

   1. Install Docker desktop on your control PC
   1. Install Github desktop on youe control PC
   1. Clone the Donuts/Voyager git repository
      1. ```cd /path/where/donuts/will/live```
      1. ```git clone https://github.com/jmccormac01/donuts_voyager.git```
      1. ```cd donuts_voyager```
   1. Edit the ```docker-compose.yml``` file to set the following information for your system:
      1. On line 16 replace the ```/Users/jmcc/Dropbox/Docker/mysql``` section of the line (before the :) with the path to where you'd like to store the database contents
      1. Ensure that folder exists before continuing
   1. For security reasons, the MySQL database root password is not stored on github. Do the following to set a root password:
      1. ```cd /path/where/donuts/lives```
      1. ```mkdir secrets/```
      1. ```cd secrets/```
      1. Create a file called ```mysql_root``` with no file extension
      1. Inside that file save the desired root password.
      1. This root password file should not be commited to any git repository.
      1. Anything in the ```secrets/``` folder is automatically excluded from version control in the ```.gitignore``` file
      1. Once you've memorised the root password and have built donuts (see below) and ran it a few times (see further below), you should delete the ```secrets/mysql_root``` file.
   1. Build the Docker image for Donuts/Voyager
      1. ```docker build -t voyager_donuts .```

# Running Donuts

Eventually I'll get round to making Voyager run the Donuts Docker container but for now
during the testing phase we need to run the container manually using:

   1. ```cd /path/where/donuts/lives```
   1. ```docker compose up```

This command will fire up the following:

   1. The container inside which Donuts will run and interact with Voyager
   1. The MySQL database container
   1. The adminer container which allows interaction with the database via a browser on url ```localhost:8080```
      1. Users familiar with MySQL can log in as the user ```donuts``` to database ```donuts``` without a password
      1. You can also log in as user ```root``` using the password specified during installation.

# Contributors

James McCormac

# License

MIT License

Copyright (c) 2021 James McCormac

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the “Software”), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
