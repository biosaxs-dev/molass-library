"""
    Optimizer.BasinHopping.py

    overriding the original to investigate

    Copyright (c) 2023-2024, SAXS Team, KEK-PF
"""
import numpy as np
from scipy.optimize import basinhopping
from scipy.optimize._basinhopping import RandomDisplacement, AdaptiveStepsize
from scipy._lib._util import check_random_state

class CustomTakestep(AdaptiveStepsize):
    def __init__(self, *args, **kwargs):
        self.history = []
        AdaptiveStepsize.__init__(self, *args, **kwargs)

    def take_step(self, x):
        self.nstep += 1
        self.nstep_tot += 1
        if self.nstep % self.interval == 0:
            self._adjust_step_size()
        ret_x = self.takestep(x)
        self.history.append(ret_x)
        return ret_x

class BasinHopping:
    def __init__(self):
        pass

    def minimize(self, func, x0, **kwargs):

        custom = kwargs.pop('custom', False)
        if custom:
            seed = kwargs.pop('seed', None)

            # set up the np.random generator
            rng = check_random_state(seed)

            take_step = kwargs.pop('take_step', None)
            if take_step is None:

                stepsize = kwargs.pop('stepsize', 0.5)
                interval = kwargs.pop('interval', 50)
                target_accept_rate = kwargs.pop('target_accept_rate', 0.5)
                stepwise_factor = kwargs.pop('stepwise_factor', 0.9)
                disp = kwargs.pop('disp', False)

                displace = RandomDisplacement(stepsize=stepsize, random_gen=rng)
                take_step_wrapped = CustomTakestep(displace, interval=interval,
                                                     accept_rate=target_accept_rate,
                                                     factor=stepwise_factor,
                                                     verbose=disp)
                take_step = take_step_wrapped
                self.take_step = take_step
        else:
            take_step = None

        return basinhopping(func, x0, take_step=take_step, **kwargs)

    def show_history(self, optimizer, load=False):
        if load:
            history_array = np.loadtxt('history_array.dat')
        else:
            assert hasattr(self.take_step, 'history')
            history_array = np.array(self.take_step.history)
            np.savetxt('history_array.dat', history_array)

        history_dict = {}
        for p in history_array:
            sp = optimizer.split_params_simple(p)
            for k, x in enumerate(sp):
                seq = history_dict.get(k)
                if seq is None:
                    history_dict[k] = seq = []
                seq.append(x)

        keys = history_dict.keys()
        num_seqs = len(keys)

        import molass_legacy.KekLib.DebugPlot as plt
        from matplotlib.gridspec import GridSpec

        param_names = ["xr_components", "xr_baseline", "rg", "mapping", "uv_components", "uv_baseline", "(c,d)", "sec_params", "(Ti, Np)"]
        heights_    = [       8,             1,          2,      1,           2,               2,          1,         2,           1     ]
        heights = heights_[0:num_seqs]
        total_heights = np.sum(heights)
        print("total_heights=", total_heights)

        with plt.Dp(scrollable=True):
            fig = plt.figure(figsize=(12, total_heights))
            fig.suptitle("Variations of Normalized Parameters", fontsize=20)
            gs = GridSpec(total_heights, 8)
            start = 0
            for k, h in enumerate(heights):
                x = np.array(history_dict[k])
                print("x.shape=", x.shape)
                if k == 0:
                    for j, name in enumerate(["h", "mu(tR)", "sigma", "tau"]):
                        s = slice(start, start+2)
                        ax0 = fig.add_subplot(gs[s,0])
                        ax1 = fig.add_subplot(gs[s,1:])
                        start += 2
                        ax0.set_axis_off()
                        ax0.text(0.5, 0.5, name, ha="center", va="center")
                        for y in x[:,:,j].T:
                            ax1.plot(y)
                        ymin, ymax = ax1.get_ylim()
                        ax1.set_ylim(min(0, ymin), max(10, ymax))
                else:
                    s = slice(start, start+h)
                    ax0 = fig.add_subplot(gs[s,0])
                    ax1 = fig.add_subplot(gs[s,1:])
                    start += h
                    ax0.set_axis_off()
                    ax0.text(0.5, 0.5, param_names[k], ha="center", va="center")
                    for y in x.T:
                        ax1.plot(y)
                    ymin, ymax = ax1.get_ylim()
                    ax1.set_ylim(min(0, ymin), max(10, ymax))

            fig.tight_layout()
            dp = plt.get_dp()
            def resize():
                from molass_legacy.KekLib.TkUtils import split_geometry
                dp.update()
                geometry = dp.geometry()
                w, h, x, y = split_geometry(geometry)
                print(geometry)
                dp.geometry("%dx%d+%d+%d" % (w, min(900, h), x, y))
            dp.after(100, resize)
            plt.show()
