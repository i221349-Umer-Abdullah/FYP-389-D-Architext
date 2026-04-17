export const lineRevealContainer = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.14,
    },
  },
};

export const lineRevealItem = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.72,
      ease: [0.16, 1, 0.3, 1] as const,
    },
  },
};

// Origami / louvre unfold — each slat pivots from its top edge
export const unfoldContainer = {
  hidden: {},
  visible: {
    transition: { staggerChildren: 0.2 },
  },
};

export const unfoldSlat = {
  hidden: { rotateX: -90, opacity: 0 },
  visible: {
    rotateX: 0,
    opacity: 1,
    transition: { duration: 0.76, ease: [0.16, 1, 0.3, 1] as const },
  },
};

export const cardRevealItem = {
  hidden: { opacity: 0, scale: 0.9, y: 16 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: {
      duration: 0.68,
      ease: [0.16, 1, 0.3, 1] as const,
    },
  },
};
