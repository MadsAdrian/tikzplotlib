# -*- coding: utf-8 -*-
#
import os
import tempfile
from importlib import import_module
import hashlib
import subprocess
from PIL import Image
import imagehash
from matplotlib import pyplot as pp

import matplotlib2tikz
import testfunctions


def test_generator():
    for name in testfunctions.__all__:
        print(name)
        test = import_module('testfunctions.' + name)
        yield check_hash, test, name


def check_hash(test, name):
    # import the test
    test.plot()
    # convert to tikz file
    handle, tmp_base = tempfile.mkstemp(prefix=name)
    tikz_file = tmp_base + '_tikz.tex'
    matplotlib2tikz.save(
        tikz_file,
        figurewidth='7.5cm',
        show_info=False
        )

    # save reference figure
    mpl_reference = tmp_base + '_reference.pdf'
    pp.savefig(mpl_reference)

    # create a latex wrapper for the tikz
    wrapper = '''\\documentclass{standalone}
\\usepackage{pgfplots}
\\usepgfplotslibrary{groupplots}
\\pgfplotsset{compat=newest}
\\begin{document}
\\input{%s}
\\end{document}''' % tikz_file
    tex_file = tmp_base + '.tex'
    with open(tex_file, 'w') as f:
        f.write(wrapper)

    # change into the directory of the TeX file
    os.chdir(os.path.dirname(tex_file))

    # compile the output to pdf
    FNULL = open(os.devnull, 'w')
    subprocess.check_call(
        # use pdflatex for now until travis features a more modern lualatex
        ['pdflatex', '--interaction=nonstopmode', tex_file],
        stdout=FNULL,
        stderr=subprocess.STDOUT
        )
    pdf_file = tmp_base + '.pdf'

    # Convert PDF to PNG.
    subprocess.check_call(
        ['pdftoppm', '-rx', '600', '-ry', '600', '-png', pdf_file, tmp_base],
        stdout=FNULL,
        stderr=subprocess.STDOUT
        )
    png_file = tmp_base + '-1.png'

    # compute the phash of the PNG
    phash = imagehash.phash(Image.open(png_file)).__str__()

    if test.phash != phash:
        # Compute the Hamming distance between the two 64-bit numbers
        hamming_dist = bin(int(phash, 16) ^ int(test.phash, 16)).count('1')
        print('Output file: %s' % png_file)
        print('computed pHash:  %s' % phash)
        print('reference pHash: %s' % test.phash)
        print(
            'Hamming distance: %s (out of %s)' %
            (hamming_dist, 4 * len(phash))
            )
        if 'DISPLAY' not in os.environ:
            # upload to chunk.io if we're on a headless client
            print('Uploading output PDF file to...')
            subprocess.check_call(
                ['curl', '-sT', pdf_file, 'chunk.io'],
                stderr=subprocess.STDOUT
                )
            print('Uploading output PNG file to...')
            subprocess.check_call(
                ['curl', '-sT', png_file, 'chunk.io'],
                stderr=subprocess.STDOUT
                )
            print('Uploading reference matplotlib PDF file to...')
            subprocess.check_call(
                ['curl', '-sT', mpl_reference, 'chunk.io'],
                stderr=subprocess.STDOUT
                )

    assert test.phash == phash
