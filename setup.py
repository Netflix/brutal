from setuptools import setup, find_packages

setup(
    name='brutal-bot',
    version='0.1.0',

    description='brutal-bot, another awful chat bot.',

    author='Corey Bertram',
    author_email='corey@qr7.com',

    url='https://github.com/q/brutal-bot',

    scripts=['brutal/bin/brutal-overlord.py',],

    include_package_data=True,
    packages = find_packages(),

    license='LICENSE',

    install_requires = [
        'Twisted >= 12.1.0',
    ],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Framework :: Twisted',
        'Operating System :: OS Independent',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Topic :: Communications :: Chat',
        'Topic :: Communications :: Chat :: Internet Relay Chat',
    ],


    #zip_safe=False,
)