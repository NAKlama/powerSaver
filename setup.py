# powerSaver - Save power by controlling processes and services
# Copyright (C) 2021  Nina Alexandra Klama
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from distutils.core import setup
import version

setup(
    name="powerSaver",
    description="Save power by controlling processes and services",
    version=version.PROGRAM_VERSION,
    license="GPLv3",
    author="Nina Alexandra Klama",
    author_email="gitlab@fklama.de",
    install_requires=[
        'psutil',
        'PyYAML',
        'funcy',
    ],
)
