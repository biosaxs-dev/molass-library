"""
Decompose.VaryUtils.py
"""
import numpy as np
import matplotlib.pyplot as plt
from molass.SEC.Models.Simple import egh

def plot_varied_decompositions(x, y, proportions, rgcurve=None, best=None, debug=False):
    if debug:
        from importlib import reload
        import molass.Decompose.Proportional
        reload(molass.Decompose.Proportional)
    from molass.Decompose.Proportional import decompose_proportionally

    proportions = np.asarray(proportions)
    num_trials, num_components = proportions.shape
    trials = np.array([f'Trial {i+1}' for i in np.arange(num_trials)])

    normalized_proportions = []
    values = []
    results = []
    for props in proportions:
        props_ = props/np.sum(props)
        normalized_proportions.append(props_)
        result = decompose_proportionally(x, y, props_)
        values.append(result.fun)
        results.append(result)
    bottom = np.zeros(num_trials)
    values = np.array(values)

    if best is not None:
       lowest_indices = np.argpartition(values, best-1)[:best]

    fig1, axes = plt.subplots(nrows=2, ncols=4, figsize=(20, 8), sharex=True)

    for i, ax in enumerate(axes.flat):
        if i < num_trials:
            if best is not None:
                if i in lowest_indices:
                    ax.set_facecolor('lightcyan')

            ax.plot(x, y, color='gray', alpha=0.5)
            cy_list = []
            for params in results[i].x.reshape((num_components, 4)):
                cy = egh(x, *params)
                ax.plot(x, cy, ':')
                cy_list.append(cy)
            ty = np.sum(cy_list, axis=0)
            ax.plot(x, ty, color='red', alpha=0.3)
            props_str = ", ".join(["%.3g" % p for p in normalized_proportions[i]])
            ax.set_title("%s - Proportions: [%s]" % (trials[i], props_str))
            ax.legend()
            if rgcurve is not None:
                axt = ax.twinx()
                axt.set_ylabel("$R_g$")
                cm = plt.get_cmap('YlGn')
                x_ = x[rgcurve.indeces]
                axt.grid(False)
                sc = axt.scatter(x_, rgcurve.rgvalues, c=rgcurve.scores, s=3, cmap=cm)

    fig2, ax = plt.subplots()
    ax.set_title("Variation of Proportion and Objective Function Value")
    for species, props_row in enumerate(np.array(normalized_proportions).T):
        # 
        ax.bar(trials, props_row, label=f'Species: {species+1}', bottom=bottom, alpha=0.3)
        bottom += props_row
    ax.legend(loc='lower left')
    ax.set_ylabel("Proportion")
    ax.set_xlabel("Trials")

    axt = ax.twinx()
    axt.plot(trials, values, 'o-', color='C3', alpha=0.5, label='Objective function value')
    if best is not None:
        label = "Best %d" % best
        axt.scatter(trials[lowest_indices], values[lowest_indices], color='C3', s=50, edgecolor='k', label=label)
    axt.set_ylabel("Objective function value")
    axt.legend(loc='upper right')