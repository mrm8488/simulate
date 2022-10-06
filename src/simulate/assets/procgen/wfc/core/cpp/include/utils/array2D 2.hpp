//================================================================================
//MIT License
//
//Copyright (c) 2018-2019 Mathieu Fehr and Nathanaël Courant
//
//Permission is hereby granted, free of charge, to any person obtaining a copy
//of this software and associated documentation files (the "Software"), to deal
//in the Software without restriction, including without limitation the rights
//to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
//copies of the Software, and to permit persons to whom the Software is
//furnished to do so, subject to the following conditions:
//
//The above copyright notice and this permission notice shall be included in all
//copies or substantial portions of the Software.
//
//THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
//IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
//FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
//AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
//LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
//OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
//SOFTWARE.
//
//1. Boost Software License - Version 1.0 - August 17th, 2003
//--------------------------------------------------------------------------------
//
//Copyright (c) 2006, 2007 Marcin Kalicinski
//
//Permission is hereby granted, free of charge, to any person or organization
//obtaining a copy of the software and accompanying documentation covered by
//this license (the "Software") to use, reproduce, display, distribute,
//execute, and transmit the Software, and to prepare derivative works of the
//Software, and to permit third-parties to whom the Software is furnished to
//do so, all subject to the following:
//
//The copyright notices in the Software and this entire statement, including
//the above license grant, this restriction and the following disclaimer,
//must be included in all copies of the Software, in whole or in part, and
//all derivative works of the Software, unless such copies or derivative
//works are solely in the form of machine-executable object code generated by
//a source language processor.
//
//THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
//IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
//FITNESS FOR A PARTICULAR PURPOSE, TITLE AND NON-INFRINGEMENT. IN NO EVENT
//SHALL THE COPYRIGHT HOLDERS OR ANYONE DISTRIBUTING THE SOFTWARE BE LIABLE
//FOR ANY DAMAGES OR OTHER LIABILITY, WHETHER IN CONTRACT, TORT OR OTHERWISE,
//ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
//DEALINGS IN THE SOFTWARE.
//
//2. The MIT License
//--------------------------------------------------------------------------------
//
//Copyright (c) 2006, 2007 Marcin Kalicinski
//
//Permission is hereby granted, free of charge, to any person obtaining a copy
//of this software and associated documentation files (the "Software"), to deal
//in the Software without restriction, including without limitation the rights
//to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
//of the Software, and to permit persons to whom the Software is furnished to do so,
//subject to the following conditions:
//
//The above copyright notice and this permission notice shall be included in all
//copies or substantial portions of the Software.
//
//THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
//IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
//FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
//THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
//LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
//OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
//IN THE SOFTWARE.
//
//================================================================================

#ifndef FAST_WFC_UTILS_ARRAY2D_HPP_
#define FAST_WFC_UTILS_ARRAY2D_HPP_

#include "assert.h"
#include "id_pair.hpp"
#include <vector>

/**
 * Represent a 2D array.
 * The 2D array is stored in a single array, to improve cache usage.
 */
template <typename T> class Array2D {

public:
  /**
   * Height and width of the 2D array.
   */
  std::size_t height;
  std::size_t width;

  /**
   * The array containing the data of the 2D array.
   */
  std::vector<T> data;

  /**
   * Build a 2D array given its height and width.
   * All the array elements are initialized to default value.
   */
  Array2D(std::size_t height, std::size_t width) noexcept
      : height(height), width(width), data(width * height) {}

  /**
   * Build a 2D array given its height and width.
   * All the array elements are initialized to value.
   */
  Array2D(std::size_t height, std::size_t width, T value) noexcept
      : height(height), width(width), data(width * height, value) {}

  /**
   * Return a const reference to the element in the i-th line and j-th column.
   * i must be lower than height and j lower than width.
   */
  const T &get(std::size_t i, std::size_t j) const noexcept {
    assert(i < height && j < width);
    return data[j + i * width];
  }

  /**
   * Return a reference to the element in the i-th line and j-th column.
   * i must be lower than height and j lower than width.
   */
  T &get(std::size_t i, std::size_t j) noexcept {
    assert(i < height && j < width);
    return data[j + i * width];
  }

  /**
   * Return the current 2D array reflected along the x axis.
   */
  Array2D<T> reflected() const noexcept {
    Array2D<T> result = Array2D<T>(width, height);
    for (std::size_t y = 0; y < height; y++) {
      for (std::size_t x = 0; x < width; x++) {
        result.get(y, x) = get(y, width - 1 - x);
      }
    }
    return result;
  }

  /**
   * Return the current 2D array rotated 90° anticlockwise
   */
  Array2D<T> rotated() const noexcept {
    Array2D<T> result = Array2D<T>(width, height);
    for (std::size_t y = 0; y < width; y++) {
      for (std::size_t x = 0; x < height; x++) {
        result.get(y, x) = get(x, width - 1 - y);
      }
    }
    return result;
  }

  /**
   * Return the sub 2D array starting from (y,x) and with size (sub_width,
   * sub_height). The current 2D array is considered toric for this operation.
   */
  Array2D<T> get_sub_array(std::size_t y, std::size_t x, std::size_t sub_width,
                           std::size_t sub_height) const noexcept {
    Array2D<T> sub_array_2d = Array2D<T>(sub_width, sub_height);
    for (std::size_t ki = 0; ki < sub_height; ki++) {
      for (std::size_t kj = 0; kj < sub_width; kj++) {
        sub_array_2d.get(ki, kj) = get((y + ki) % height, (x + kj) % width);
      }
    }
    return sub_array_2d;
  }

  /**
   * Check if two 2D arrays are equals.
   */
  bool operator==(const Array2D<T> &a) const noexcept {
    if (height != a.height || width != a.width) {
      return false;
    }

    for (std::size_t i = 0; i < data.size(); i++) {
      if (a.data[i] != data[i]) {
        return false;
      }
    }
    return true;
  }
};

template<> inline Array2D<IdPair> Array2D<IdPair>::rotated() const noexcept {
  Array2D<IdPair> result = Array2D<IdPair>(width, height);
    for (std::size_t y = 0; y < width; y++) {
      for (std::size_t x = 0; x < height; x++) {
        
        IdPair original = get(x, width - 1 - y);

        if(original.reflected == 1) {
          original.rotation = (original.rotation + 3) % 4;
        } else {
          original.rotation = (original.rotation + 1) % 4;
        }

        result.get(y, x) = original;
      }
    }
    return result;
}

template<> inline Array2D<IdPair> Array2D<IdPair>::reflected() const noexcept {
  Array2D<IdPair> result = Array2D<IdPair>(width, height);
    for (std::size_t y = 0; y < height; y++) {
      for (std::size_t x = 0; x < width; x++) {
        IdPair original = get(y, width - 1 - x);
        original.reflected = (original.reflected + 1) % 2;
        result.get(y, x) = original;
      }
    }
    return result;
}

/**
 * Hash function.
 */
namespace std {
template <typename T> class hash<Array2D<T>> {
public:
  std::size_t operator()(const Array2D<T> &a) const noexcept {
    std::size_t seed = a.data.size();
    for (const T &i : a.data) {
      seed ^= hash<T>()(i) + (std::size_t)0x9e3779b9 + (seed << 6) + (seed >> 2);
    }
    return seed;
  }
};
} // namespace std

#endif // FAST_WFC_UTILS_ARRAY2D_HPP_
