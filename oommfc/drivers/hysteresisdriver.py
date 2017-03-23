from .driver import Driver


class HysteresisDriver(Driver):
    def __init__(self):
        super().__init__()

        # Hrange is for booking for hysteresis.

        # We follow OOMMF's use of Hrange as explained at
        # http://math.nist.gov/oommf/doc/userguide12a3/userguide/Standard_Oxs_Ext_Child_Clas.html#UZ

        self.Hrange = None

        # override the documentation string of the drive methods
        # provided by the parent class
        self.drive.__func__.__doc__ = """
        arguments to this function are
        either:
        - `Hmin`  : vector for start field
        - `Hmax`  : vector for end field
        - `n`     : number of hysteresis steps to be computed between
                    Hmin and Hmax

        Or:
        - `Hrange` : a list of sequence specification, where each sequence
                     specification reads [H1x H1y H1z H2x H2y H2z n] and
                     describes part of a hysteresis loop in which the field
                     starts at H1 and increases to H2 in n steps.

        Examples:

        drive(Hmin=[-1, 0, 0], Hmax=[1, 0, 0], n=50) will compute a
           hysteresis loop where the applied field changes from Hmin to Hmax
           in 50 steps, and then the field is changed back to Hmin (in another
           50 steps).

        drive(Hrange=[[-1, 0, 0, 1, 0, 0, 50], [1, 0, 0, -1, 0, 0, 200]]) will
           compute the same hysteresis loop, but use 200 steps on the way back
           (and 50 while the x component of the field is increasing.)

        The `Hrange` argument call is the most flexible version (and identical
        to what is implemented in OOMMF's [1] hysteresis zeeman field).
        The `Hmax`, `Hmin` and `n` version is a convenience for a common
        use case.

        [1] http://math.nist.gov/oommf/doc/userguide12a3/userguide/Standard_Oxs_Ext_Child_Clas.html#UZ

        """


    def _script(self, system, **kwargs):
        assert self.Hrange is not None, "_check_args was not called. Error"

        meshname = system.m.mesh.name
        systemname = system.name
        Hrange = self.Hrange

        mif = "# m0 file\n"
        mif += "Specify Oxs_FileVectorField:m0file {\n"
        mif += "   atlas :atlas\n"
        mif += "   file m0.omf\n"
        mif += "}\n\n"

        mif += "# UZeeman\n"
        mif += "Specify Oxs_UZeeman {\n"
        mif += "  Hrange {\n"
        for subloop in Hrange:
            mif += "    {{ {} {} {} {} {} {} {} }}\n".format(*subloop)
        mif += "  }\n"
        mif += "}\n\n"
        mif += "# CGEvolver\n"
        mif += "Specify Oxs_CGEvolve {}\n\n"
        mif += "# MinDriver\n"
        mif += "Specify Oxs_MinDriver {\n"
        mif += "  evolver Oxs_CGEvolve\n"
        mif += "  stopping_mxHxm 0.01\n"
        mif += "  mesh :{}\n".format(meshname)
        mif += "  Ms {\n"
        mif += "    Oxs_VecMagScalarField {\n"
        mif += "      field :m0file\n"
        mif += "    }\n"
        mif += "  }\n"
        mif += "  m0 :m0file\n"
        mif += "  basename {}\n".format(systemname)
        mif += "  scalar_field_output_format {text %\#.15g}\n"
        mif += "  vector_field_output_format {text %\#.15g}\n"
        mif += "}\n\n"
        mif += "Destination table mmArchive\n"
        mif += "Destination mags mmArchive\n\n"
        mif += "Schedule DataTable table Stage 1\n"
        mif += "Schedule Oxs_MinDriver::Magnetization mags Stage 1"

        return mif

    def _check_args(self, **kwargs):
        if 'Hmin' in kwargs and 'Hmax' in kwargs and 'n' in kwargs:

            Hmin = kwargs["Hmin"]
            Hmax = kwargs["Hmax"]
            n = kwargs["n"]

            if len(Hmin) != 3:
                raise ValueError("Expected length 3 tuple")
            if len(Hmax) != 3:
                raise ValueError("Expected length 3 tuple")
            if n <= 0 or not isinstance(n, int):
                raise ValueError("Expected n > 0.")

            Hrange = [list(Hmin) + list(Hmax) + [n], \
                      list(Hmax) + list(Hmin) + [n]]

            if 'Hrange' in kwargs:
                print("kwargs = {}".format(kwargs))
                raise ValueError("Seems we have an entry for 'Hrange' already??")
            assert self.Hrange == None
            self.Hrange = Hrange

            # see http://math.nist.gov/oommf/doc/userguide12a3/userguide/Standard_Oxs_Ext_Child_Clas.html#UZ
        elif 'Hrange' in kwargs:
            pass
            # check that Hrange is list (or at least iterable)
            assert isinstance(list(Hrange), list)
            # check that each item in Hrange has seven items:
            assert len(Hrange) >= 1
            for subloop in Hrange:
                assert len(subloop) == 7, "desired format is [H1x, H1y, H1z, " +\
                      "H2x, H2y, H2z, n] but received {}.".format(subloop)
            self.Hrange = Hrange

        else:
            raise RuntimeError("need 'Hrange' or 'Hmin' and 'Hmax' and'n' in input to hysteresis.\s" +
                               "Found kwargs = {}.".format(kwargs))
        return kwargs
