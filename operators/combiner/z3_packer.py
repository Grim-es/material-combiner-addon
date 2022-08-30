import z3
from itertools import combinations

class UnsatError(Exception):
    pass

class Z3Packer:
    po2_sizes = [
        (128, 128), (256, 128), (128, 256),
        (256, 256), (512, 256), (256, 512),
        (512, 512), (1024, 512), (512, 1024),
        (1024, 1024), (2048, 1024), (1024, 2048),
        (2048, 2048), (4096, 2048), (2048, 4096),
        (4096, 4096), (8192, 4096), (4096, 8192),
        (8192, 8192), (16384, 8192), (8192, 16384),
        (16384, 16384)
    ]

    def __init__(self, images, mode='PO2', width=0, height=0, timeout=5000):
        '''
        mode can be 'PO2', 'QUAD', 'AUTO', 'CUST'
        '''
        self.original_images = images
        self.images = [img for img in images.values()]

        print(self.images[0]['gfx'])
        self.sym_image = [(z3.Int(f'img_{i}_x'), z3.Int(f'img_{i}_y')) for i in range(len(self.images))]
        self.model_max_height = z3.Int('max_height')
        self.model_max_width = z3.Int('max_width')
        self.total_pixels = sum([img['gfx']['size'][0] * img['gfx']['size'][1] for img in self.images])
        self.max_height = 0
        self.max_width = 0
        self.mode = mode
        self.timeout = timeout

    def sym_max(self, x, y):
        return z3.If(x > y, x, y)

    def __get_po2_candidates(self):
        '''
        gets the potential size candidates for PO2
        '''
        for i in range(len(self.po2_sizes)):
            if (self.po2_sizes[i][0] * self.po2_sizes[i][1]) >= self.total_pixels:
                return self.po2_sizes[i:]
        return []

    def __constrain_images(self):
        '''
        adds common constraints to the solver
        '''
        # ensure the images don't overlap with each other
        for pair in combinations(range(len(self.images)), 2):
            a = pair[0]
            a_tl = self.sym_image[a]
            a_br = (a_tl[0] + self.images[a]['gfx']['size'][0], a_tl[1] + self.images[a]['gfx']['size'][1])

            b = pair[1]
            b_tl = self.sym_image[b]
            b_br = (b_tl[0] + self.images[b]['gfx']['size'][0], b_tl[1] + self.images[b]['gfx']['size'][1])

            self.s.add(z3.Or(a_tl[0] >= b_br[0], b_tl[0] >= a_br[0],
                a_br[1] <= b_tl[1], b_br[1] <= a_tl[1]))


        sym_max_width = 0
        sym_max_height = 0

        # ensure the images are within the bounds of the atlas
        for i in range(len(self.images)):
            sym_img = self.sym_image[i]
            img = self.images[i]
            self.s.add([sym_img[0] >= 0, sym_img[1] >= 0])
            sym_max_width = self.sym_max(sym_max_width, sym_img[0] + img['gfx']['size'][0])
            sym_max_height = self.sym_max(sym_max_height, sym_img[1] + img['gfx']['size'][1])

        self.s.add(self.model_max_height == sym_max_height)
        self.s.add(self.model_max_width == sym_max_width)

    def __push_size_constriants(self, width, height):
        '''
        pushes a backtracking point and constrains the size of the atlas
        '''
        self.s.push()
        if width == 0 and height == 0:
            return

        for i in range(len(self.images)):
            sym_img = self.sym_image[i]
            img = self.images[i]
            if width > 0:
                self.s.add((sym_img[0] + img['gfx']['size'][0]) <= width)
            if height > 0:
                self.s.add((sym_img[1] + img['gfx']['size'][1]) <= height)


    def __optimize(self):
        '''
        optimizes the atlas size (rather than solving for a particular size)
        '''
        if not isinstance(self.s, z3.Optimize):
            raise ValueError('optimize can only be called when mode is QUAD or AUTO')

        self.s.minimize(self.model_max_height + self.model_max_width)
        return self.__check()


    def __solve(self):
        '''
        solves the atlas size (rather than optimizing to be a minimal size)
        '''
        if not isinstance(self.s, z3.Solver):
            raise ValueError('solve can only be called when mode is PO2 or CUST')

        return self.__check()

    def __check(self):
        '''
        checks the solver for satisfiability and returns the result if satisfiable
        '''
        result = self.s.check()
        if result == z3.sat:
            model = self.s.model()
            print("z3_packer: solved model:", model)
            for i in range(len(self.images)):
                sym_img = self.sym_image[i]
                img = self.images[i]
                img['gfx']['fit'] = {
                    'x': model[sym_img[0]].as_long(),
                    'y': model[sym_img[1]].as_long()
                }
        elif result == z3.unsat:
            raise UnsatError('The constraints given were unsatisfiable (not possible to fit ' +
                'images in atlas). Try increasing the maximum size of the atlas.')
        else:
            raise UnsatError('The constraints given were unsatisfiable in the time limit given. ' +
                'Try increasing the timeout or maximum size of the atlas.')

        return self.original_images

    def fit(self):
        '''
        fits the images to the atlas
        '''
        if self.max_width < 0 or self.max_height < 0:
            raise ValueError('max width and height must be positive')

        if self.mode in ['PO2', 'CUST']:
            self.s = z3.Solver()
        elif self.mode in ['QUAD', 'AUTO']:
            self.s = z3.Optimize()
        else:
            raise ValueError('mode must be PO2, QUAD, AUTO, or CUST')

        self.s.set('timeout', self.timeout)

        if self.mode == 'CUST':
            if self.max_width == 0 or self.max_height == 0:
                raise ValueError('width and height must both be specified when running in CUST mode')

        self.__constrain_images()

        if self.mode == 'PO2' and (self.max_width == 0 or self.max_height == 0):
            candidates = self.__get_po2_candidates()
            for po2_candidate in candidates[:4]:
                candidate = po2_candidate
                if self.max_width > 0:
                    candidate = (min(self.max_width, candidate[0]), candidate[1])
                if self.max_height > 0:
                    candidate = (candidate[0], min(self.max_height, candidate[1]))
                self.__push_size_constriants(*candidate)
                try:
                    return self.__solve()
                except UnsatError:
                    pass

                # reset the constraints on each attempt
                self.s.pop()

            raise UnsatError('Attempted all candidates and none were satisfiable. Your final ' +
                'atlas size is likely beyond 16384x16384 which is unsupported')

        self.__push_size_constriants(self.max_width, self.max_height)

        if isinstance(self.s, z3.Optimize):
            return self.__optimize()

        return self.__solve()
