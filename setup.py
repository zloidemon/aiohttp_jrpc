from setuptools import setup, find_packages
import os
import re


def read_version():
    regexp = re.compile(r"^__version__\W*=\W*'([\d.]+)'")
    init_py = os.path.join(os.path.dirname(__file__),
                           'aiohttp_jrpc', '__init__.py')
    with open(init_py) as fp:
        for line in fp:
            match = regexp.match(line)
            if match is not None:
                return match.group(1)
        else:
            raise RuntimeError('Cannot find version')


def read(f):
    return open(os.path.join(os.path.dirname(__file__), f)).read().strip()

install_requires = ['aiohttp>=0.17', 'validictory']
tests_require = install_requires + ['pytest']


setup(name='aiohttp_jrpc',
      version=read_version(),
      packages=find_packages(),
      install_requires=install_requires,
      tests_require=tests_require,
      test_suite='nose.collector',
      author='Veniamin Gvozdikov',
      author_email='g.veniamin@googlemail.com',
      description=('JSON RPC protocol for aiohttp.web '
                   '(http server for asyncio)'),
      long_description='\n\n'.join((read('README.rst'), read('CHANGES.txt'))),
      keywords='aiohttp jsonrpc rpc',
      platforms=['any'],
      url='https://github.com/zloidemon/aiohttp_jrpc/',
      license='BSD',
      classifiers=[
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.4',
          'Programming Language :: Python :: 3.5',
          'Programming Language :: Python',
          'Topic :: Internet :: WWW/HTTP'],
      include_package_data=True)
