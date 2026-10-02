/** @type {import('tailwindcss').Config} */
export default {
  // Bật `class` thay vì để mặc định `prefers-color-scheme`.
  //
  // Vì sao: ~6 component dùng tiền tố `dark:`, nhưng cấu hình KHÔNG khai báo
  // darkMode nên Tailwind mặc định bám theo hệ điều hành. Kết quả: trên máy
  // người dùng bật chế độ tối, các thẻ KPI đổi nền tối nằm lọt trong khung
  // sáng `bg-[#F8FAFC]` — đọc gần như không nổi, và banner "Demo Offline" đổi
  // sang chữ tối trên nền sáng. Người dùng không có nút bật/tắt nào để chọn.
  // `class` để ứng dụng tự quyết định (xem main.tsx), nên trạng thái không còn
  // phụ thuộc thiết bị.
  darkMode: 'class',
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        // Đăng ký Plus Jakarta Sans vào `font-sans` để `font-sans` (dùng ở
        // App.tsx và hầu hết page) thật sự dùng font này. Trước đây font chỉ được
        // gắn ở <body> bằng class arbitrary nhưng App.tsx lại đặt `font-sans`
        // (ui-sans-serif, system-ui...) ở gốc ứng dụng nên ghi đè — font tải về
        // không bao giờ được dùng, tốn băng thông mà không có tác dụng.
        sans: [
          "'Plus Jakarta Sans'",
          'ui-sans-serif',
          'system-ui',
          '-apple-system',
          'Segoe UI',
          'sans-serif',
        ],
      },
      colors: {
        brand: {
          50: '#f0fdf4',
          100: '#dcfce7',
          500: '#22c55e',
          600: '#16a34a',
        },
        sidebar: {
          bg: '#0F172A',
          hover: '#1E293B',
          text: '#94A3B8',
          active: '#FFFFFF'
        }
      }
    },
  },
  plugins: [],
}

