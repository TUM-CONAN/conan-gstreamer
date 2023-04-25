cmake_minimum_required(VERSION 3.15)
cmake_policy(SET CMP0074 NEW)

project(test_package C)
set(CMAKE_VERBOSE_MAKEFILE TRUE)

find_package(glib REQUIRED CONFIG)
find_package(gstreamer REQUIRED CONFIG)

add_executable(${PROJECT_NAME} test_package.c)
target_link_libraries(${PROJECT_NAME}
    gstreamer::gstreamer-1.0 gstreamer::gstreamer-base-1.0 gstreamer::gstreamer-controller-1.0
    gstreamer::gstreamer-net-1.0 gstreamer::gstreamer-check-1.0 glib::glib)
if (TARGET gstreamer::gstcoreelements)
    target_link_libraries(${PROJECT_NAME} gstreamer::gstcoreelements)
endif ()
