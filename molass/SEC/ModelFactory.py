"""
SEC.ModelFactory.py
"""
from importlib import reload

def create_model(model_name, **kwargs):
    """
    Create a model based on the model name.

    Parameters
    ----------
    model_name : str
        The name of the model to create.
    kwargs : dict
        Additional parameters to pass to the model constructor.
        
    Returns
    -------
    model : object
        The created model object.
    """
    debug = kwargs.get('debug', False)
    model_name = model_name.lower()
    if model_name == 'sdm':
        if debug:
            import molass.SEC.Models.SDM
            reload(molass.SEC.Models.SDM)
        from molass.SEC.Models.SDM import SDM
        return SDM(**kwargs)
    elif model_name == 'edm':
        if debug:
            import molass.SEC.Models.EDM
            reload(molass.SEC.Models.EDM)   
        from molass.SEC.Models.EDM import EDM
        return EDM(**kwargs)
    else:
        raise ValueError(f"Unknown model name: {model_name}")