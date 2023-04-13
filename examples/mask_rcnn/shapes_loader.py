from paz.abstract.loader import Loader
import numpy as np
from paz.backend.image.draw import draw_circle, draw_triangle, draw_square
from paz.backend.boxes import apply_non_max_suppression
import random


class Shapes(Loader):
    """ Loader for shapes synthetic dataset.

    # Arguments
        num_samples: Int indicating number of samples to load.
        image_size: (height, width) of input image to load.
        split: String determining the data split to load.
            e.g. `train`, `val` or `test`
        class_names: List of strings or `all`.
        iou_thresh: Float intersection over union.
        max_num_shapes: Int. maximum number of shapes in the image.

    # Returns
        List of dictionaries with keys `image`, `mask`, `box_data`
            containing
    """
    def __init__(self, num_samples, image_size, split='train',
                 class_names='all', iou_thresh=0.3, max_num_shapes=4):
        if class_names == 'all':
            class_names = ['BG', 'square', 'circle', 'triangle']
        self.name_to_arg = dict(zip(class_names, range(len(class_names))))
        self.arg_to_name = dict(zip(range(len(class_names)), class_names))
        self.num_samples, self.image_size = num_samples, image_size
        self.labels = ['image', 'masks', 'box_data']
        self.iou_thresh = iou_thresh
        self.max_num_shapes = max_num_shapes
        super(Shapes, self).__init__(None, split, class_names, 'Shapes')

    def load_data(self):
        return [self.load_sample() for arg in range(self.num_samples)]

    def load_sample(self):
        shapes = self._sample_shapes(self.max_num_shapes, *self.image_size)
        boxes = self._compute_bounding_boxes(shapes)
        shapes, boxes = self._filter_shapes(boxes, shapes, self.iou_thresh)
        image = self._draw_shapes(shapes)
        masks = self._draw_masks(shapes)
        class_args = [self.name_to_arg[name[0]] for name in shapes]
        class_args = np.asarray(class_args).reshape(-1, 1)
        box_data = np.concatenate([boxes, class_args], axis=1)
        sample = dict(zip(self.labels, [image, masks, box_data]))
        return sample

    def _sample_shape(self, H, W, offset=20):
        shape = random.choice(self.class_names[1:])
        color = tuple(np.random.randint(0, 255, size=3).tolist())
        center_x = random.randint(offset, W - offset - 1)
        center_y = random.randint(offset, H - offset - 1)
        size = random.randint(offset, H // 4)
        return shape, color, (center_x, center_y, size)

    def _sample_shapes(self, num_shapes, H, W, offset=20):
        shapes = []
        N = random.randint(1, num_shapes)
        for shape_arg in range(N):
            shapes.append(self._sample_shape(H, W, offset=20))
        return shapes

    def _compute_bounding_box(self, center_x, center_y, size):
        x_min, y_min = center_x - size, center_y - size
        x_max, y_max = center_x + size, center_y + size
        box = [x_min, y_min, x_max, y_max]
        return box

    def _compute_bounding_boxes(self, shapes):
        boxes = []
        for shape in shapes:
            center_x, center_y, size = shape[2]
            box = self._compute_bounding_box(center_x, center_y, size)
            boxes.append(box)
        return np.asarray(boxes)

    def _filter_shapes(self, boxes, shapes, iou_thresh):
        scores = np.ones(len(boxes))  # all shapes have the same score np.arange(N)
        args, num_boxes = apply_non_max_suppression(boxes, scores, iou_thresh)
        box_args = args[:num_boxes]
        selected_shapes = []
        for box_arg in box_args:
            selected_shapes.append(shapes[box_arg])
        return selected_shapes, boxes[box_args]

    def _draw_shapes(self, shapes):
        H, W = self.image_size
        background_color = np.random.randint(0, 255, size=3)
        image = np.ones([H, W, 3], dtype=np.uint8)
        image = image * background_color.astype(np.uint8)
        for shape, color, dimensions in shapes:
            image = self._draw_shape(image, shape, dimensions, color)
        return image

    def _draw_shape(self, image, shape, dimensions, color):
        center_x, center_y, size = dimensions
        functions = [draw_square, draw_circle, draw_triangle]
        draw = dict(zip(self.class_names[1:], functions))
        image = draw[shape](image, (center_x, center_y), color, size)
        return image

    def _draw_masks(self, shapes):
        H, W = self.image_size
        class_masks = []
        for class_mask in range(self.max_num_shapes):
            class_masks.append(np.zeros([H, W, 1]))
        for shape_arg, (shape, color, dimensions) in enumerate(shapes):
            class_mask = self._draw_shape(
                class_masks[shape_arg], shape, dimensions, (1, 1, 1))
            class_masks[shape_arg] = class_mask

        masks = np.concatenate(class_masks, axis=-1).astype(np.uint8)

        for i in range(masks.shape[-1]):

            for j in range(i + 1, masks.shape[-1]):
                occulusions = np.logical_and(masks[:, :, i], masks[:, :, j])
                masks[:, :, i] = np.logical_xor(masks[:, :, i], occulusions).astype(np.uint8)

        return masks
