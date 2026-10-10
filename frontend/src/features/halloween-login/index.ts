/**
 * Điểm vào duy nhất của cảnh đăng nhập Halloween.
 *
 * React chỉ canh việc gắn/tháo; toàn bộ hiệu ứng nằm trong các module con như
 * bản HTML tĩnh gốc. Trả về hàm dọn dẹp để gỡ sạch listener và class trên
 * `<body>` khi rời trang đăng nhập.
 */

import { startScene } from './scene';
import { startSpider } from './spider';
import { startWolf } from './wolf';

export function startHalloweenScene(): () => void {
  const teardowns = [startScene(), startWolf(), startSpider()];
  return () => {
    teardowns.forEach((teardown) => teardown());
  };
}
