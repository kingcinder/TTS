import os, platform

def pick_backend(order: str):
    """Decide which backend to use according to the user's order preference.
    order: string like "rocm,dml,cpu"
    Returns: "rocm" | "cuda" | "dml" | "cpu"
    """
    items = [x.strip() for x in order.split(',') if x.strip()]

    # Try ROCm (HIP appears via torch.cuda with AMD devices)
    try:
        import torch
        if 'rocm' in items and torch.cuda.is_available():
            name = torch.cuda.get_device_name(0)
            if any(k in name for k in ('AMD', 'Radeon')):
                os.environ['HIP_VISIBLE_DEVICES'] = '0'
                return 'rocm'
    except Exception:
        pass

    # (Optional) Try CUDA if the user explicitly requested it
    try:
        import torch
        if 'cuda' in items and torch.cuda.is_available():
            return 'cuda'
    except Exception:
        pass

    # Try DirectML (Windows)
    try:
        if 'dml' in items and platform.system() == 'Windows':
            import torch_directml as dml  # noqa
            _ = dml.device(0)
            return 'dml'
    except Exception:
        pass

    return 'cpu'
