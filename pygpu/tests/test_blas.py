import numpy

from .support import (guard_devsup, gen_gpuarray, context)

try:
    import scipy.linalg.blas
    try:
        fblas = scipy.linalg.blas.fblas
    except AttributeError:
        fblas = scipy.linalg.blas
except ImportError, e:
    raise SkipTest("no scipy blas to compare against")

import pygpu.blas as gblas


def test_gemv():
    for shape in [(100, 128), (128, 50), (0, 10), (0, 0), (10, 0)]:
        for order in ['f', 'c']:
            for trans in [False, True]:
                for offseted_i in [True, False]:
                    for sliced in [1, 2, -1, -2]:
                        yield gemv, shape, 'float32', order, trans, \
                            offseted_i, sliced, True, False
    for overwrite in [True, False]:
        for init_y in [True, False]:
            yield gemv, (4, 3), 'float32', 'f', False, False, 1, \
                overwrite, init_y
    yield gemv, (32, 32), 'float64', 'f', False, False, 1, True, False
    for alpha in [0, 1, -1, 0.6]:
        for beta in [0, 1, -1, 0.6]:
            for overwite in [True, False]:
                yield gemv, (32, 32), 'float32', 'f', False, False, 1, \
                    overwrite, True, alpha, beta


@guard_devsup
def gemv(shp, dtype, order, trans, offseted_i, sliced,
         overwrite, init_y, alpha=1.0, beta=0.0):
    cA, gA = gen_gpuarray(shp, dtype, order=order, offseted_inner=offseted_i,
                          sliced=sliced, ctx=context)
    if trans:
        shpX = (shp[0],)
        shpY = (shp[1],)
    else:
        shpX = (shp[1],)
        shpY = (shp[0],)
    cX, gX = gen_gpuarray(shpX, dtype, offseted_inner=offseted_i,
                          sliced=sliced, ctx=context)
    if init_y:
        cY, gY = gen_gpuarray(shpY, dtype, ctx=context)
    else:
        cY, gY = None, None

    if shp[0] == 0 or shp[1] == 0:
        #scipy fblas don't like empty input
        if trans:
            cA = cA.T
        cr = alpha * numpy.dot(cA, cX)
        if cY is not None:
            cr += beta * cY
    elif dtype == 'float32':
        cr = fblas.sgemv(alpha, cA, cX, beta, cY, trans=trans,
                         overwrite_y=overwrite)
    else:
        cr = fblas.dgemv(alpha, cA, cX, beta, cY, trans=trans,
                         overwrite_y=overwrite)
    gr = gblas.gemv(alpha, gA, gX, beta, gY, trans_a=trans,
                    overwrite_y=overwrite)

    numpy.testing.assert_allclose(cr, numpy.asarray(gr), rtol=1e-6)


def test_gemm():
    for m, n, k in [(48, 15, 32), (15, 32, 48),
                    (0, 32, 48), (15, 0, 48), (15, 32, 0),
                    (0, 0, 48), (15, 0, 0), (0, 32, 0),
                    (0, 0, 0)
                ]:
        for order in [('f', 'f', 'f'), ('c', 'c', 'c'),
                      ('f', 'f', 'c'), ('f', 'c', 'f'),
                      ('f', 'c', 'c'), ('c', 'f', 'f'),
                      ('c', 'f', 'c'), ('c', 'c', 'f')]:
            for trans in [(False, False), (True, True),
                          (False, True), (True, False)]:
                for offseted_o in [False, True]:
                    yield gemm, m, n, k, 'float32', order, trans, \
                        offseted_o, 1, False, False
    for sliced in [1, 2, -1, -2]:
        for overwrite in [True, False]:
            for init_res in [True, False]:
                yield gemm, 4, 3, 2, 'float32', ('f', 'f', 'f'), \
                    (False, False), False, sliced, overwrite, init_res
    yield gemm, 32, 32, 32, 'float64', ('f', 'f', 'f'), (False, False), \
        False, 1, False, False
    for alpha in [0, 1, -1, 0.6]:
        for beta in [0, 1, -1, 0.6]:
            for overwrite in [True, False]:
                yield gemm, 32, 23, 32, 'float32', ('f', 'f', 'f'), \
                    (False, False), False, 1, overwrite, True, alpha, beta

@guard_devsup
def gemm(m, n, k, dtype, order, trans, offseted_o, sliced, overwrite,
         init_res, alpha=1.0, beta=0.0):
    if trans[0]:
        shpA = (k,m)
    else:
        shpA = (m,k)
    if trans[1]:
        shpB = (n,k)
    else:
        shpB = (k,n)

    cA, gA = gen_gpuarray(shpA, dtype, order=order[0],
                          offseted_outer=offseted_o,
                          sliced=sliced, ctx=context)
    cB, gB = gen_gpuarray(shpB, dtype, order=order[1],
                          offseted_outer=offseted_o,
                          sliced=sliced, ctx=context)
    if init_res:
        cC, gC = gen_gpuarray((m,n), dtype, order=order[2], ctx=context)
    else:
        cC, gC = None, None
    if k == 0 or m == 0 or n == 0:
        #scipy fblas don't like empty input
        if trans[0]:
            cA = cA.T
        if trans[1]:
            cB = cB.T
        cr = alpha * numpy.dot(cA, cB)
        if cC:
            cr += beta * cC
    elif dtype == 'float32':
        cr = fblas.sgemm(alpha, cA, cB, beta, cC, trans_a=trans[0],
                         trans_b=trans[1], overwrite_c=overwrite)
    else:
        cr = fblas.dgemm(alpha, cA, cB, beta, cC, trans_a=trans[0],
                         trans_b=trans[1], overwrite_c=overwrite)
    gr = gblas.gemm(alpha, gA, gB, beta, gC, trans_a=trans[0],
                    trans_b=trans[1], overwrite_c=overwrite)

    numpy.testing.assert_allclose(cr, numpy.asarray(gr), rtol=1e-6)
