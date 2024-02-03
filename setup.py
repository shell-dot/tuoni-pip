from distutils.core import setup
setup(
  name = 'TuoniLib',
  packages = ['TuoniLib'],
  version = '0.1.1',
  license='MIT', 
  description = 'Library to interact with Tuoni C2 API',
  author = 'Jaanus Kääp',
  author_email = 'jaanus.kaap@gmail.com',
  url = 'https://github.com/shell-dot/TuoniLib',
  download_url = 'https://github.com/shell-dot/TuoniLib/archive/refs/tags/v_01_1.tar.gz',
  keywords = ['TUONI'],
  install_requires=['requests'],
  classifiers=[
    'Development Status :: 3 - Alpha',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',      # Define that your audience are developers
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',   # Again, pick a license
    'Programming Language :: Python :: 3',      #Specify which pyhton versions that you want to support
    'Programming Language :: Python :: 3.4',
    'Programming Language :: Python :: 3.5',
    'Programming Language :: Python :: 3.6',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
    'Programming Language :: Python :: 3.11',
    'Programming Language :: Python :: 3.12',
  ],
)