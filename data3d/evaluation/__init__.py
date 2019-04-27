from .suncg import suncg_evaluation


def evaluate(dataset, predictions, output_folder, **kwargs):
    """evaluate dataset using different methods based on dataset type.
    Args:
        dataset: Dataset object
        predictions(list[BoxList]): each item in the list represents the
            prediction results for one image.
        output_folder: output folder, to save evaluation files or results.
        **kwargs: other args.
    Returns:
        evaluation result
    """

    args = dict(
        dataset=dataset, predictions=predictions, output_folder=output_folder, **kwargs
    )

    return suncg_evaluation(**args)