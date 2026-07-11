import hashlib, os, json, pprint,re


def print(string):
    pprint.pprint(string)


def hash_str(string):
    """Create a hash for a string.

    Parameters
    ----------
    string : str
        A string

    Returns
    -------
    hash_id: str
        A unique id defining the string
    """
    hash_id = hashlib.md5(string.encode()).hexdigest()
    return hash_id


def hash_dict(exp_dict):
    """Create a hash for an experiment.

    Parameters
    ----------
    exp_dict : dict
        An experiment, which is a single set of hyper-parameters

    Returns
    -------
    hash_id: str
        A unique id defining the experiment
    """
    dict2hash = ""
    if not isinstance(exp_dict, dict):
        raise ValueError("exp_dict is not a dict")

    for k in sorted(exp_dict.keys()):
        if "." in k:
            raise ValueError(". has special purpose")
        elif isinstance(exp_dict[k], dict):
            v = hash_dict(exp_dict[k])
        elif isinstance(exp_dict[k], tuple):
            raise ValueError(
                f"{exp_dict[k]} tuples can't be hashed yet, consider converting tuples to lists"
            )
        elif (
            isinstance(exp_dict[k], list)
            and len(exp_dict[k])
            and isinstance(exp_dict[k][0], dict)
        ):
            v_str = ""
            for e in exp_dict[k]:
                if isinstance(e, dict):
                    v_str += hash_dict(e)
                else:
                    raise ValueError("all have to be dicts")
            v = v_str
        else:
            v = exp_dict[k]

        dict2hash += str(k) + "/" + str(v)
    hash_id = hashlib.md5(dict2hash.encode()).hexdigest()

    return hash_id


def save_json(fname, data, makedirs=True):
    """Save data into a json file.

    Parameters
    ----------
    fname : str
        Name of the json file
    data : [type]
        Data to save into the json file
    makedirs : bool, optional
        If enabled creates the folder for saving the file, by default True
    """
    # turn fname to string in case it is a Path object
    fname = str(fname)
    dirname = os.path.dirname(fname)
    if makedirs and dirname != "":
        os.makedirs(dirname, exist_ok=True)
    with open(fname, "w") as json_file:
        json.dump(data, json_file, indent=4, sort_keys=True)


def load_json(fname, decode=None):  # TODO: decode???
    """Load a json file.

    Parameters
    ----------
    fname : str
        Name of the file
    decode : [type], optional
        [description], by default None

    Returns
    -------
    [type]
        Content of the file
    """
    with open(fname, "r") as json_file:
        d = json.load(json_file)

    return d


def load_tree_dict(path, node_dict):
    try:
        # 确保路径格式正确
        pattern = r"([^/]+)\.json$"
        match = re.search(pattern, path)
        if not match:
            raise ValueError(f"文件路径 {path} 格式不正确，无法解析 JSON 文件名")
        match_name = match.group(1)

        # 确保文件存在
        file_path = r"C:\Users\wxf\Desktop\autobench\data\insight_tree.json"
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件 {file_path} 不存在")

        # 读取 JSON 数据
        with open(file_path, 'r', encoding='utf-8') as f:
            data_list = json.load(f)

        # 获取 gt_insight_tree
        gt_insight_tree = []
        for item in data_list:
            if item.get("data") == match_name:
                gt_insight_tree = item.get("insight_tree", [])
                break

        # 确保 score_dict 是一个可迭代的列表
        if not isinstance(node_dict, list):
            raise TypeError("score_dict 应为列表类型")

        # 获取 gt 洞察 ID 与预测洞察 ID 的映射关系
        reflect_dict = {str(i+1): o.get('pred_id') for i, o in enumerate(node_dict) if isinstance(o, dict)}

        return gt_insight_tree, reflect_dict

    except (FileNotFoundError, json.JSONDecodeError, ValueError, TypeError) as e:
        print(f"错误：{e}")
        return None, None